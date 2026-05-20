"""Model manager page.

Layout
------
Header row: title + Refresh button
Token row:  optional HF token for gated/private models
Downloads:  one progress card per active download (hidden when idle)
CTkTabview
  Discover   — live HuggingFace catalog (text-to-image, sorted by downloads)
  Installed  — locally installed models with delete buttons
  Diagnostics — environment / package checks
"""
import threading
import customtkinter as ctk

from ..theme import *
from ...core.manager import (
    list_models, download_model, delete_model,
    browse_hub_models, is_model_installed, run_diagnostics,
)


def _fmt_count(n: int) -> str:
    """Format a large integer as e.g. '12.3M' or '4.5K'."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _fmt_eta(seconds: int) -> str:
    """Format ETA seconds as a human-readable string."""
    if seconds <= 0:
        return ""
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m}m {s:02d}s"
    h, rem = divmod(seconds, 3600)
    return f"{h}h {rem // 60:02d}m"


class ModelsPage(ctk.CTkFrame):
    def __init__(self, parent, show_toast=None, **kw):
        kw.setdefault("fg_color", BG)
        super().__init__(parent, **kw)
        self._toast = show_toast

        # repo_id → {"progress": dict, "stop_event": Event}
        self._downloads: dict[str, dict] = {}
        # repo_id → {"card": CTkFrame, "bar": CTkProgressBar, "pct": CTkLabel, "msg": CTkLabel}
        self._dl_cards:  dict[str, dict] = {}

        self._catalog: list[dict] = []
        self._build()
        self.after(100, self._load_installed)
        self.after(200, self._fetch_catalog)

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)   # tabview expands

        # ── Header ────────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 0))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(hdr, text="Models", font=F_XL, text_color=TEXT,
                     ).grid(row=0, column=0, sticky="w")

        self._refresh_btn = ctk.CTkButton(
            hdr, text="Refresh", width=90, height=32, font=F_SM,
            fg_color=BG_CARD, hover_color=BG_HOVER, text_color=TEXT_SEC,
            corner_radius=8, command=self._refresh,
        )
        self._refresh_btn.grid(row=0, column=1)

        # ── Token row ─────────────────────────────────────────────────────────
        tok_row = ctk.CTkFrame(self, fg_color="transparent")
        tok_row.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 6))
        tok_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(tok_row, text="HF Token", font=F_SM_B, text_color=TEXT_SEC,
                     ).grid(row=0, column=0, padx=(0, 10))
        self._token_var = ctk.StringVar()
        ctk.CTkEntry(
            tok_row, textvariable=self._token_var,
            placeholder_text="Optional — required for gated/private models",
            show="•", height=32, font=F_SM,
            fg_color=BG_INPUT, text_color=TEXT,
            border_color=BORDER, corner_radius=8,
        ).grid(row=0, column=1, sticky="ew")

        # ── Active downloads container ────────────────────────────────────────
        # One download card is packed inside here per active download.
        # Hidden when no downloads are running.
        self._dl_container = ctk.CTkFrame(self, fg_color="transparent")
        self._dl_container.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 4))
        self._dl_container.grid_columnconfigure(0, weight=1)
        self._dl_container.grid_remove()

        # ── Tab view ──────────────────────────────────────────────────────────
        self._tabs = ctk.CTkTabview(
            self, fg_color=BG_PANEL,
            segmented_button_fg_color=BG_CARD,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_HOVER,
            segmented_button_unselected_color=BG_CARD,
            segmented_button_unselected_hover_color=BG_HOVER,
            text_color=TEXT, text_color_disabled=TEXT_MUTED,
            border_color=BORDER, border_width=1,
            corner_radius=12,
        )
        self._tabs.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self._tabs.add("Discover")
        self._tabs.add("Installed")
        self._tabs.add("Diagnostics")

        self._build_discover_tab(self._tabs.tab("Discover"))
        self._build_installed_tab(self._tabs.tab("Installed"))
        self._build_diagnostics_tab(self._tabs.tab("Diagnostics"))

    def _build_discover_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        self._catalog_loading = ctk.CTkLabel(
            parent, text="Fetching popular models from HuggingFace…",
            font=F_MD, text_color=TEXT_MUTED,
        )
        self._catalog_loading.grid(row=0, column=0, pady=40)

        self._catalog_scroll = ctk.CTkScrollableFrame(
            parent, fg_color="transparent", scrollbar_button_color=BG_HOVER,
        )
        self._catalog_scroll.grid(row=0, column=0, sticky="nsew")
        self._catalog_scroll.grid_columnconfigure(0, weight=1)
        self._catalog_scroll.grid_remove()

    def _build_installed_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        self._installed_scroll = ctk.CTkScrollableFrame(
            parent, fg_color="transparent", scrollbar_button_color=BG_HOVER,
        )
        self._installed_scroll.grid(row=0, column=0, sticky="nsew")
        self._installed_scroll.grid_columnconfigure(0, weight=1)

    # ── Discover: fetch catalog ───────────────────────────────────────────────
    def _fetch_catalog(self):
        self._catalog_loading.configure(
            text="Fetching popular models from HuggingFace…")
        self._catalog_loading.grid()
        self._catalog_scroll.grid_remove()
        token = self._token_var.get().strip() or None

        def _run():
            try:
                models = browse_hub_models(task="text-to-image", limit=40, token=token)
                self.after(0, lambda: self._render_catalog(models, error=None))
            except Exception as exc:
                err = str(exc)   # capture before `exc` goes out of scope (Python 3.12+)
                self.after(0, lambda: self._render_catalog([], error=err))

        threading.Thread(target=_run, daemon=True).start()

    def _render_catalog(self, models: list, error: str | None = None):
        self._catalog = models
        self._catalog_loading.grid_remove()

        for w in self._catalog_scroll.winfo_children():
            w.destroy()

        if not models:
            msg  = error or "No results returned."
            hint = "\n\nOpen the Diagnostics tab for details." if error else ""
            ctk.CTkLabel(
                self._catalog_scroll,
                text=msg + hint,
                font=F_SM, text_color=DANGER if error else TEXT_MUTED,
                justify="left", wraplength=560,
            ).grid(row=0, column=0, pady=30, padx=10, sticky="w")
            self._catalog_scroll.grid()
            return

        for i, m in enumerate(models):
            self._catalog_card(self._catalog_scroll, m, row=i)

        self._catalog_scroll.grid()

    def _catalog_card(self, parent, m: dict, row: int):
        repo_id   = m["repo_id"]
        name      = m["name"]
        author    = m["author"]
        downloads = _fmt_count(m.get("downloads", 0))
        likes     = _fmt_count(m.get("likes", 0))
        size_str      = m.get("size_str", "")
        installed     = is_model_installed(repo_id)
        is_current_dl = repo_id in self._downloads

        card = ctk.CTkFrame(
            parent, fg_color=BG_CARD, corner_radius=10,
            border_color=BORDER, border_width=1,
        )
        card.grid(row=row, column=0, sticky="ew", pady=3)
        card.grid_columnconfigure(1, weight=1)

        # Icon badge
        gem = ctk.CTkFrame(card, width=40, height=40, corner_radius=8,
                           fg_color=ACCENT_TINT_CARD)
        gem.grid(row=0, column=0, padx=(12, 10), pady=10)
        gem.grid_propagate(False)
        ctk.CTkLabel(gem, text="◆", font=(FONT_FACE, 16),
                     text_color=ACCENT).place(relx=0.5, rely=0.5, anchor="center")

        # Info block
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=0, column=1, sticky="ew", pady=10)

        ctk.CTkLabel(info, text=name, font=F_MD_B, text_color=TEXT,
                     anchor="w").pack(fill="x")

        meta_row = ctk.CTkFrame(info, fg_color="transparent")
        meta_row.pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(meta_row, text=f"by {author}", font=F_SM,
                     text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(meta_row, text=f"   {downloads} dl",
                     font=F_SM, text_color=TEXT_SEC).pack(side="left")
        ctk.CTkLabel(meta_row, text=f"   {likes} likes",
                     font=F_SM, text_color=TEXT_SEC).pack(side="left")
        if size_str:
            ctk.CTkLabel(meta_row, text=f"   {size_str}",
                         font=F_SM, text_color=ACCENT).pack(side="left")

        # Action button / badge
        if is_current_dl:
            ctk.CTkLabel(card, text="Downloading...", font=F_SM_B,
                         text_color=ACCENT).grid(row=0, column=2, padx=(0, 14))
        elif installed:
            ctk.CTkLabel(card, text="Installed", font=F_SM_B,
                         text_color=SUCCESS).grid(row=0, column=2, padx=(0, 14))
        else:
            ctk.CTkButton(
                card, text="Download", width=100, height=34, font=F_SM_B,
                fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#fff",
                corner_radius=8,
                command=lambda r=repo_id: self._start_download(r),
            ).grid(row=0, column=2, padx=(0, 12), pady=10)

    # ── Installed tab ─────────────────────────────────────────────────────────
    def _load_installed(self):
        def _run():
            try:
                data = [m.to_dict() for m in list_models()]
            except Exception:
                data = []
            self.after(0, lambda: self._render_installed(data))

        threading.Thread(target=_run, daemon=True).start()

    def _render_installed(self, models: list):
        for w in self._installed_scroll.winfo_children():
            w.destroy()

        if not models:
            ctk.CTkLabel(
                self._installed_scroll,
                text="No models installed yet.\nUse the Discover tab to download one.",
                font=F_MD, text_color=TEXT_MUTED, justify="center",
            ).grid(row=0, column=0, pady=40)
            return

        for i, m in enumerate(models):
            self._installed_row(m, row=i)

    def _installed_row(self, m: dict, row: int):
        name     = m.get("alias") or m.get("repo_id", "Unknown")
        mtype    = m.get("type", "SD")
        size     = m.get("size_gb")
        mid      = m.get("model_id", "")
        size_str = f"{size:.1f} GB" if size else "unknown size"

        card = ctk.CTkFrame(
            self._installed_scroll, fg_color=BG_CARD, corner_radius=10,
            border_color=BORDER, border_width=1,
        )
        card.grid(row=row, column=0, sticky="ew", pady=3)
        card.grid_columnconfigure(1, weight=1)

        gem = ctk.CTkFrame(card, width=40, height=40, corner_radius=8,
                           fg_color=ACCENT_TINT_CARD)
        gem.grid(row=0, column=0, padx=(12, 10), pady=10)
        gem.grid_propagate(False)
        ctk.CTkLabel(gem, text="◆", font=(FONT_FACE, 16),
                     text_color=ACCENT).place(relx=0.5, rely=0.5, anchor="center")

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=0, column=1, sticky="ew", pady=10)
        ctk.CTkLabel(info, text=name, font=F_MD_B, text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(info, text=f"{mtype}  ·  {size_str}",
                     font=F_SM, text_color=TEXT_SEC).pack(anchor="w")

        ctk.CTkButton(
            card, text="X", width=32, height=32, font=F_SM_B,
            fg_color="transparent", hover_color=blend_hex(DANGER, BG_CARD, 0.25),
            text_color=DANGER, corner_radius=8,
            command=lambda _id=mid: self._delete_model(_id),
        ).grid(row=0, column=2, padx=(0, 10))

    # ── Download: start ───────────────────────────────────────────────────────
    def _start_download(self, repo_id: str):
        if repo_id in self._downloads:
            if self._toast:
                self._toast("This model is already downloading.", "info")
            return

        stop_ev = threading.Event()
        prog = {
            "progress": 0.0, "message": "", "speed_mbps": 0.0,
            "eta_seconds": 0, "done": False, "error": None,
        }
        self._downloads[repo_id] = {"progress": prog, "stop_event": stop_ev}
        self._add_dl_card(repo_id)
        self._render_catalog(self._catalog)   # update badges in Discover tab

        token = self._token_var.get().strip() or None

        def _run():
            try:
                download_model(
                    repo_id=repo_id, token=token,
                    progress=prog, stop_event=stop_ev,
                )
            except Exception as e:
                prog["done"]  = True
                prog["error"] = str(e)

        threading.Thread(target=_run, daemon=True).start()

        # Start poll loop only when the first download begins
        if len(self._downloads) == 1:
            self.after(300, self._poll_all_downloads)

    # ── Download: progress card UI ────────────────────────────────────────────
    def _add_dl_card(self, repo_id: str):
        """Create and pack a progress card for *repo_id* into _dl_container."""
        short = repo_id.split("/")[-1] if "/" in repo_id else repo_id
        self._dl_container.grid()   # make container visible

        card = ctk.CTkFrame(
            self._dl_container, fg_color=BG_PANEL, corner_radius=10,
            border_color=ACCENT_TINT_CARD, border_width=1,
        )
        card.pack(fill="x", pady=(0, 4))
        card.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=(10, 10))
        inner.grid_columnconfigure(0, weight=1)

        # Row 0: model name  |  percentage  |  cancel button
        title_row = ctk.CTkFrame(inner, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew")
        title_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_row, text=short, font=F_SM_B, text_color=TEXT, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        pct_lbl = ctk.CTkLabel(title_row, text="0%", font=F_SM_B, text_color=ACCENT)
        pct_lbl.grid(row=0, column=1, padx=(8, 0))

        ctk.CTkButton(
            title_row, text="Cancel", width=80, height=26, font=F_SM,
            fg_color="transparent",
            hover_color=blend_hex(DANGER, BG_PANEL, 0.25),
            text_color=DANGER, corner_radius=6,
            border_color=DANGER, border_width=1,
            command=lambda r=repo_id: self._cancel_download(r),
        ).grid(row=0, column=2, padx=(10, 0))

        # Row 1: progress bar
        bar = ctk.CTkProgressBar(
            inner, height=5,
            fg_color=BG_INPUT, progress_color=ACCENT, corner_radius=3,
        )
        bar.grid(row=1, column=0, sticky="ew", pady=(5, 3))
        bar.set(0)

        # Row 2: status message (size · speed · ETA)
        msg_lbl = ctk.CTkLabel(
            inner, text="Connecting…", font=F_SM, text_color=TEXT_MUTED, anchor="w",
        )
        msg_lbl.grid(row=2, column=0, sticky="w")

        self._dl_cards[repo_id] = {
            "card": card,
            "bar":  bar,
            "pct":  pct_lbl,
            "msg":  msg_lbl,
        }

    # ── Download: poll loop ───────────────────────────────────────────────────
    def _poll_all_downloads(self):
        if not self._downloads:
            return

        finished: list[tuple[str, str | None]] = []

        for repo_id, state in list(self._downloads.items()):
            prog  = state["progress"]
            cards = self._dl_cards.get(repo_id, {})

            pct  = prog.get("progress", 0.0)
            msg  = prog.get("message", "")
            eta  = prog.get("eta_seconds", 0)
            done = prog.get("done", False)
            err  = prog.get("error")

            if bar := cards.get("bar"):
                bar.set(pct)
            if pct_lbl := cards.get("pct"):
                pct_lbl.configure(text=f"{int(pct * 100)}%")
            if msg_lbl := cards.get("msg"):
                eta_str = _fmt_eta(eta)
                full_msg = f"{msg}  ·  ETA {eta_str}" if eta_str and msg else msg
                if full_msg:
                    msg_lbl.configure(text=full_msg)

            if done:
                finished.append((repo_id, err))

        for repo_id, err in finished:
            self._finish_download(repo_id, err)

        if self._downloads:
            self.after(300, self._poll_all_downloads)
        else:
            self._dl_container.grid_remove()

    # ── Download: cancel ──────────────────────────────────────────────────────
    def _cancel_download(self, repo_id: str):
        state = self._downloads.get(repo_id)
        if state:
            state["stop_event"].set()
        # The poll loop will see done=True / error="Cancelled" and clean up

    # ── Download: finish ──────────────────────────────────────────────────────
    def _finish_download(self, repo_id: str, error: str | None):
        self._downloads.pop(repo_id, None)

        card_widgets = self._dl_cards.pop(repo_id, {})
        card = card_widgets.get("card")
        if card and card.winfo_exists():
            card.destroy()

        if error == "Cancelled":
            if self._toast:
                self._toast("Download cancelled.", "info")
        elif error:
            if self._toast:
                self._toast(f"Download failed: {error}", "error")
        else:
            if self._toast:
                self._toast("Model downloaded successfully!", "success")
            self._load_installed()

        self._render_catalog(self._catalog)   # refresh Installed / Downloading badges

        if not self._downloads:
            self._dl_container.grid_remove()

    # ── Delete ────────────────────────────────────────────────────────────────
    def _delete_model(self, model_id: str):
        def _run():
            try:
                delete_model(model_id)
            except Exception:
                pass
            self.after(0, self._load_installed)

        threading.Thread(target=_run, daemon=True).start()

    # ── Diagnostics tab ───────────────────────────────────────────────────────
    def _build_diagnostics_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        # Header row
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(4, 8))
        top.grid_columnconfigure(0, weight=1)

        self._diag_status = ctk.CTkLabel(
            top, text="Click Run to check your environment.",
            font=F_SM, text_color=TEXT_MUTED,
        )
        self._diag_status.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            top, text="Run Diagnostics", width=150, height=32, font=F_SM_B,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#fff",
            corner_radius=8, command=self._run_diagnostics,
        ).grid(row=0, column=1)

        # Results area
        self._diag_scroll = ctk.CTkScrollableFrame(
            parent, fg_color="transparent", scrollbar_button_color=BG_HOVER,
        )
        self._diag_scroll.grid(row=1, column=0, sticky="nsew")
        self._diag_scroll.grid_columnconfigure(0, weight=1)

    def _run_diagnostics(self):
        self._diag_status.configure(text="Running…", text_color=TEXT_MUTED)
        for w in self._diag_scroll.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self._diag_scroll, text="Running diagnostics…",
            font=F_MD, text_color=TEXT_MUTED,
        ).grid(row=0, column=0, pady=20)

        def _do():
            results = run_diagnostics()
            self.after(0, lambda: self._render_diagnostics(results))

        threading.Thread(target=_do, daemon=True).start()

    def _render_diagnostics(self, results: list):
        import datetime
        for w in self._diag_scroll.winfo_children():
            w.destroy()

        _STATUS_COLOUR = {
            "ok":    SUCCESS,
            "error": DANGER,
            "warn":  WARNING,
            "info":  TEXT_MUTED,
        }
        _STATUS_ICON = {"ok": "ok", "error": "err", "warn": "!", "info": "."}

        current_section = None
        r = 0
        for item in results:
            section = item["section"]

            # Section heading
            if section != current_section:
                current_section = section
                ctk.CTkLabel(
                    self._diag_scroll, text=section,
                    font=F_SM_B, text_color=TEXT_SEC,
                    anchor="w",
                ).grid(row=r, column=0, padx=4, pady=(14, 2), sticky="w")
                r += 1
                ctk.CTkFrame(
                    self._diag_scroll, height=1, fg_color=BORDER,
                ).grid(row=r, column=0, sticky="ew", padx=4, pady=(0, 4))
                r += 1

            # Data row
            colour = _STATUS_COLOUR.get(item["status"], TEXT_MUTED)
            icon   = _STATUS_ICON.get(item["status"], "·")

            row_frame = ctk.CTkFrame(
                self._diag_scroll, fg_color=BG_CARD,
                corner_radius=6,
            )
            row_frame.grid(row=r, column=0, sticky="ew", pady=2, padx=4)
            row_frame.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                row_frame, text=item["label"],
                font=F_SM_B, text_color=TEXT, width=180, anchor="w",
            ).grid(row=0, column=0, padx=(12, 8), pady=7, sticky="w")

            ctk.CTkLabel(
                row_frame, text=item["value"],
                font=F_SM, text_color=colour, anchor="w", wraplength=460,
            ).grid(row=0, column=1, padx=4, pady=7, sticky="w")

            ctk.CTkLabel(
                row_frame, text=icon,
                font=F_SM_B, text_color=colour, width=20,
            ).grid(row=0, column=2, padx=(4, 10), pady=7)

            r += 1

        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._diag_status.configure(
            text=f"Last run: {ts}",
            text_color=TEXT_MUTED,
        )

    # ── Refresh ───────────────────────────────────────────────────────────────
    def _refresh(self):
        self._fetch_catalog()
        self._load_installed()
