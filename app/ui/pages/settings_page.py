"""Settings page."""
import threading
import customtkinter as ctk
from tkinter import filedialog

from ..theme import *
from ...core.config import config


class SettingsPage(ctk.CTkFrame):
    def __init__(self, parent, show_toast=None, **kw):
        kw.setdefault("fg_color", BG)
        super().__init__(parent, **kw)
        self._toast = show_toast
        self._build()
        self._load_settings()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 0))
        ctk.CTkLabel(hdr, text="Settings", font=F_XL, text_color=TEXT).pack(side="left")

        # Scrollable content
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                        scrollbar_button_color=BG_HOVER)
        scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=14)
        scroll.grid_columnconfigure(0, weight=1)

        row = 0

        # ── Compute ───────────────────────────────────────────────────────────
        row = self._section(scroll, "Compute", row)

        self._device_var = ctk.StringVar(value="auto")
        row = self._combo_row(scroll, "Device", ["auto", "cuda", "cpu", "mps"],
                              self._device_var, row)

        self._xformers_var = ctk.BooleanVar(value=False)
        row = self._switch_row(scroll, "xFormers memory efficient attention",
                               "Reduces VRAM usage (requires xFormers install)",
                               self._xformers_var, row)

        # ── Output ────────────────────────────────────────────────────────────
        row = self._section(scroll, "Output", row)

        self._format_var = ctk.StringVar(value="png")
        row = self._combo_row(scroll, "Image format", ["png", "jpg", "webp"],
                              self._format_var, row)

        row = self._outdir_row(scroll, row)

        # ── Appearance ────────────────────────────────────────────────────────
        row = self._section(scroll, "Appearance", row)

        self._theme_var = ctk.StringVar(value="dark")
        row = self._combo_row(scroll, "Theme", ["dark", "light", "system"],
                              self._theme_var, row)

        # ── Save button ───────────────────────────────────────────────────────
        ctk.CTkFrame(scroll, height=1, fg_color=BORDER
                     ).grid(row=row, column=0, padx=0, pady=12, sticky="ew")
        row += 1

        self._save_btn = ctk.CTkButton(
            scroll, text="Save Settings", height=44, font=F_MD_B,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#fff",
            corner_radius=8, command=self._save,
        )
        self._save_btn.grid(row=row, column=0, sticky="ew", pady=(0, 20))
        row += 1

        # ── Developer Options (hidden by default) ─────────────────────────────
        self._dev_expanded = False

        self._dev_toggle = ctk.CTkButton(
            scroll, text="Developer Options  (show)",
            height=28, font=F_SM,
            fg_color="transparent", hover_color=BG_HOVER,
            text_color=TEXT_MUTED, corner_radius=6, anchor="w",
            command=self._toggle_dev,
        )
        self._dev_toggle.grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1

        self._dev_panel = ctk.CTkFrame(scroll, fg_color="transparent")
        self._dev_panel.grid(row=row, column=0, sticky="ew", pady=(0, 20))
        self._dev_panel.grid_columnconfigure(0, weight=1)
        self._dev_panel.grid_remove()   # hidden until toggled
        self._build_dev_panel(self._dev_panel)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _section(self, parent, title: str, row: int) -> int:
        if row > 0:
            ctk.CTkFrame(parent, height=1, fg_color=BORDER
                         ).grid(row=row, column=0, padx=0, pady=(8, 0), sticky="ew")
            row += 1
        ctk.CTkLabel(parent, text=title, font=F_LG_B, text_color=TEXT
                     ).grid(row=row, column=0, padx=0, pady=(14, 8), sticky="w")
        return row + 1

    def _combo_row(self, parent, label: str, values: list,
                   variable: ctk.StringVar, row: int) -> int:
        card = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=10,
                            border_color=BORDER, border_width=1)
        card.grid(row=row, column=0, sticky="ew", pady=4)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=label, font=F_MD, text_color=TEXT
                     ).grid(row=0, column=0, padx=16, pady=12, sticky="w")
        ctk.CTkComboBox(card, values=values, variable=variable, width=160,
                        font=F_MD, fg_color=BG_INPUT, text_color=TEXT,
                        border_color=BORDER, button_color=BG_HOVER,
                        dropdown_fg_color=BG_CARD, corner_radius=8
                        ).grid(row=0, column=1, padx=(0, 16), pady=12)
        return row + 1

    def _switch_row(self, parent, label: str, hint: str,
                    variable: ctk.BooleanVar, row: int) -> int:
        card = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=10,
                            border_color=BORDER, border_width=1)
        card.grid(row=row, column=0, sticky="ew", pady=4)
        card.grid_columnconfigure(0, weight=1)
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=0, column=0, padx=16, pady=12, sticky="ew")
        ctk.CTkLabel(info, text=label, font=F_MD, text_color=TEXT).pack(anchor="w")
        if hint:
            ctk.CTkLabel(info, text=hint, font=F_SM, text_color=TEXT_MUTED).pack(anchor="w")
        ctk.CTkSwitch(card, text="", variable=variable,
                      onvalue=True, offvalue=False,
                      fg_color=BG_INPUT, progress_color=ACCENT
                      ).grid(row=0, column=1, padx=(0, 16), pady=12)
        return row + 1

    def _outdir_row(self, parent, row: int) -> int:
        self._outdir_var = ctk.StringVar(value="")
        card = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=10,
                            border_color=BORDER, border_width=1)
        card.grid(row=row, column=0, sticky="ew", pady=4)
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Output directory", font=F_MD, text_color=TEXT
                     ).grid(row=0, column=0, padx=16, pady=12, sticky="w")
        ctk.CTkLabel(card, textvariable=self._outdir_var,
                     font=F_SM, text_color=TEXT_SEC, anchor="e", wraplength=300
                     ).grid(row=0, column=1, padx=8, pady=12, sticky="ew")
        ctk.CTkButton(card, text="Browse…", width=90, height=30, font=F_SM,
                      fg_color=BG_CARD, hover_color=BG_HOVER, text_color=TEXT_SEC,
                      corner_radius=8, command=self._pick_outdir
                      ).grid(row=0, column=2, padx=(0, 16), pady=12)
        return row + 1

    def _pick_outdir(self):
        p = filedialog.askdirectory()
        if p:
            self._outdir_var.set(p)

    # ── Developer Options ─────────────────────────────────────────────────────
    def _toggle_dev(self):
        self._dev_expanded = not self._dev_expanded
        if self._dev_expanded:
            self._dev_panel.grid()
            self._dev_toggle.configure(text="Developer Options  (hide)")
        else:
            self._dev_panel.grid_remove()
            self._dev_toggle.configure(text="Developer Options  (show)")

    def _build_dev_panel(self, parent):
        from ...core.fonts import font_dir_paths
        proj_dir, data_dir = font_dir_paths()

        card = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=10,
                            border_color=BORDER, border_width=1)
        card.grid(row=0, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        # ── Heading ───────────────────────────────────────────────────────────
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 2))
        ctk.CTkLabel(head, text="Custom UI Font",
                     font=F_MD_B, text_color=TEXT).pack(side="left")

        # ── Drop-folder hint ──────────────────────────────────────────────────
        hint = ctk.CTkFrame(card, fg_color=BG_INPUT, corner_radius=6)
        hint.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 10))
        hint.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(hint,
                     text="Drop .ttf or .otf files into either directory, then click Scan:",
                     font=F_SM, text_color=TEXT_SEC, anchor="w",
                     ).grid(row=0, column=0, padx=10, pady=(8, 2), sticky="w")
        ctk.CTkLabel(hint, text=str(proj_dir),
                     font=F_SM, text_color=TEXT_MUTED, anchor="w",
                     ).grid(row=1, column=0, padx=10, pady=(0, 2), sticky="w")
        ctk.CTkLabel(hint, text=str(data_dir),
                     font=F_SM, text_color=TEXT_MUTED, anchor="w",
                     ).grid(row=2, column=0, padx=10, pady=(0, 8), sticky="w")

        # ── Font picker ───────────────────────────────────────────────────────
        picker = ctk.CTkFrame(card, fg_color="transparent")
        picker.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 6))
        picker.grid_columnconfigure(0, weight=1)

        self._font_map: dict[str, dict] = {}   # display name → font dict

        self._font_combo = ctk.CTkComboBox(
            picker, values=["No fonts found — add files and click Scan"],
            width=300, height=34, font=F_SM,
            fg_color=BG_INPUT, text_color=TEXT,
            border_color=BORDER, button_color=BG_HOVER,
            dropdown_fg_color=BG_CARD, corner_radius=8,
            state="readonly",
        )
        self._font_combo.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            picker, text="Scan", width=70, height=34, font=F_SM_B,
            fg_color=BG_CARD, hover_color=BG_HOVER, text_color=TEXT_SEC,
            corner_radius=8, command=self._scan_fonts,
        ).grid(row=0, column=1, padx=(8, 0))

        # ── Action buttons ────────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=3, column=0, sticky="w", padx=16, pady=(0, 10))

        self._font_apply_btn = ctk.CTkButton(
            btn_row, text="Apply Font", width=120, height=32, font=F_SM_B,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#fff",
            corner_radius=8, command=self._apply_font,
        )
        self._font_apply_btn.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Reset to System Font", width=160, height=32, font=F_SM,
            fg_color=BG_CARD, hover_color=BG_HOVER, text_color=TEXT_SEC,
            corner_radius=8, command=self._reset_font,
        ).pack(side="left")

        # ── Status label ──────────────────────────────────────────────────────
        self._font_status_lbl = ctk.CTkLabel(
            card, text="", font=F_SM, text_color=TEXT_MUTED,
            anchor="w", wraplength=500,
        )
        self._font_status_lbl.grid(row=4, column=0, sticky="ew",
                                   padx=16, pady=(0, 14))

        # Populate on first show
        self._scan_fonts(silent=True)

    def _scan_fonts(self, silent: bool = False):
        """Scan font directories and refresh the combo box."""
        from ...core.fonts import scan_font_dirs
        fonts = scan_font_dirs()
        self._font_map = {f["name"]: f for f in fonts}

        if not fonts:
            self._font_combo.configure(
                values=["No fonts found — add files and click Scan"])
            self._font_combo.set("No fonts found — add files and click Scan")
            if not silent:
                self._font_status("No fonts found. Add .ttf/.otf files to either directory.")
            return

        names = list(self._font_map.keys())
        self._font_combo.configure(values=names)

        # Pre-select the currently active font if it's in the list
        current = config.custom_font
        match = next((f["name"] for f in fonts if f["family"] == current), None)
        self._font_combo.set(match or names[0])

        if not silent:
            self._font_status(f"{len(fonts)} font(s) found.")

    def _apply_font(self):
        selected = self._font_combo.get()
        font_info = self._font_map.get(selected)
        if not font_info:
            self._font_status("No font selected. Click Scan first.", error=True)
            return

        family = font_info["family"]
        path   = font_info["path"]

        self._font_apply_btn.configure(state="disabled", text="Applying…")
        self._font_status(f"Registering '{family}'…")

        def _run():
            from ...core.fonts import register_font
            ok = register_font(path)
            config.update(custom_font=family)
            self.after(0, lambda: self._font_done(family, ok))

        threading.Thread(target=_run, daemon=True).start()

    def _font_done(self, family: str, ok: bool):
        self._font_apply_btn.configure(state="normal", text="Apply Font")
        if ok:
            self._font_status(
                f"'{family}' set as UI font. Restart PyForge to apply.",
                success=True,
            )
        else:
            self._font_status(
                f"'{family}' saved to config but OS registration may have failed. "
                "Restart to check.",
                success=True,
            )

    def _reset_font(self):
        config.update(custom_font="")
        # Re-scan so the combo reflects no selection
        self._scan_fonts(silent=True)
        self._font_status("Reset to system font. Restart PyForge to apply.",
                          success=True)

    def _font_status(self, text: str, error: bool = False, success: bool = False):
        colour = DANGER if error else (SUCCESS if success else TEXT_MUTED)
        self._font_status_lbl.configure(text=text, text_color=colour)

    # ── Load / Save ───────────────────────────────────────────────────────────
    def _load_settings(self):
        d = config.as_dict()
        self._device_var.set(d.get("device", "auto"))
        self._xformers_var.set(d.get("xformers", False))
        self._format_var.set(d.get("image_format", "png").lower())
        self._outdir_var.set(d.get("outputs_dir", ""))
        self._theme_var.set(d.get("theme", "dark"))

        # Populate the Developer Options font picker
        family = d.get("custom_font", "")
        if family:
            self._font_status(f"Active custom font: {family}  (restart applied this)")

    def _save(self):
        theme = self._theme_var.get()
        config.update(
            device       = self._device_var.get(),
            xformers     = self._xformers_var.get(),
            image_format = self._format_var.get().upper(),
            outputs_dir  = self._outdir_var.get(),
            theme        = theme,
        )
        # Apply immediately — no restart required
        ctk.set_appearance_mode(theme)
        if self._toast:
            self._toast("Settings saved.", "success")
