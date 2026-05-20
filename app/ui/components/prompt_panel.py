"""
Reusable left-hand controls panel: prompt, model selector, resolution,
steps/CFG sliders, seed/batch, and a Generate button.
"""
import threading
import customtkinter as ctk

from ..theme import *
from ...core.manager import list_models


class PromptPanel(ctk.CTkScrollableFrame):
    """
    Embeds all generation controls. Callers read .get_params() and bind
    on_generate to a callback that receives those params.
    """

    def __init__(self, parent, on_generate=None, extra_widgets_fn=None, **kw):
        kw.setdefault("fg_color", BG_PANEL)
        kw.setdefault("scrollbar_button_color", BG_HOVER)
        super().__init__(parent, **kw)
        self._on_generate = on_generate
        self._generating  = False
        self._model_ids: dict[str, str] = {}   # display-name → model_id

        self._build(extra_widgets_fn)
        self.after(200, self._load_models)

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build(self, extra_fn):
        P = self
        pad = {"padx": 14, "pady": (0, 10), "sticky": "ew"}

        # ── Prompt ────────────────────────────────────────────────────────────
        _label(P, "Prompt", "describe what you want to see", row=0)
        self._prompt = ctk.CTkTextbox(P, height=80, font=F_MD,
                                      fg_color=BG_INPUT, text_color=TEXT,
                                      border_color=BORDER, border_width=1, corner_radius=8)
        self._prompt.grid(row=1, column=0, **pad)
        self._prompt.insert("0.0", "")
        self._prompt.bind("<FocusIn>",  lambda e: self._prompt.configure(border_color=ACCENT))
        self._prompt.bind("<FocusOut>", lambda e: self._prompt.configure(border_color=BORDER))

        # ── Negative prompt ───────────────────────────────────────────────────
        _label(P, "Avoid", "what to leave out", row=2)
        self._neg = ctk.CTkTextbox(P, height=52, font=F_MD,
                                   fg_color=BG_INPUT, text_color=TEXT,
                                   border_color=BORDER, border_width=1, corner_radius=8)
        self._neg.grid(row=3, column=0, **pad)
        self._neg.bind("<FocusIn>",  lambda e: self._neg.configure(border_color=ACCENT))
        self._neg.bind("<FocusOut>", lambda e: self._neg.configure(border_color=BORDER))

        _divider(P, row=4)

        # ── Model selector ─────────────────────────────────────────────────────
        _label(P, "Model", row=5)
        mrow = ctk.CTkFrame(P, fg_color="transparent")
        mrow.grid(row=6, column=0, **pad)
        mrow.grid_columnconfigure(0, weight=1)
        self._model_combo = ctk.CTkComboBox(
            mrow, values=["Loading…"], font=F_MD,
            fg_color=BG_INPUT, text_color=TEXT,
            border_color=BORDER, button_color=BG_HOVER,
            dropdown_fg_color=BG_CARD, corner_radius=8,
        )
        self._model_combo.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(mrow, text="R", width=34, height=34, font=F_SM_B,
                      fg_color=BG_CARD, hover_color=BG_HOVER,
                      text_color=TEXT_SEC, corner_radius=8,
                      command=self._load_models).grid(row=0, column=1, padx=(6, 0))

        _divider(P, row=7)

        # ── Resolution ─────────────────────────────────────────────────────────
        _label(P, "Resolution", row=8)
        preset_row = ctk.CTkFrame(P, fg_color="transparent")
        preset_row.grid(row=9, column=0, padx=14, pady=(0, 6), sticky="ew")
        self._w_var = ctk.IntVar(value=512)
        self._h_var = ctk.IntVar(value=512)

        presets = [("512", 512, 512), ("768", 768, 768), ("1024", 1024, 1024)]
        self._preset_btns = []
        for i, (lbl, w, h) in enumerate(presets):
            b = ctk.CTkButton(
                preset_row, text=lbl, width=80, height=28, font=F_SM,
                fg_color=ACCENT, hover_color=ACCENT_HOVER,
                text_color="#fff", corner_radius=14,
                command=lambda _w=w, _h=h: self._set_res(_w, _h),
            )
            b.grid(row=0, column=i, padx=3)
            self._preset_btns.append((b, w, h))

        # Custom W × H
        cust = ctk.CTkFrame(P, fg_color="transparent")
        cust.grid(row=10, column=0, padx=14, pady=(0, 10), sticky="ew")
        _lbl(cust, "W").grid(row=0, column=0, padx=(0, 4))
        self._w_entry = _spinbox(cust, self._w_var, 256, 2048)
        self._w_entry.grid(row=0, column=1)
        _lbl(cust, "×").grid(row=0, column=2, padx=6)
        _lbl(cust, "H").grid(row=0, column=3, padx=(0, 4))
        self._h_entry = _spinbox(cust, self._h_var, 256, 2048)
        self._h_entry.grid(row=0, column=4)
        _lbl(cust, "px").grid(row=0, column=5, padx=(6, 0))

        _divider(P, row=11)

        # ── Steps ──────────────────────────────────────────────────────────────
        self._steps_var = ctk.DoubleVar(value=25)
        _label(P, "Steps", "20–30 is great · more = more detail, slower", row=12)
        _slider_row(P, self._steps_var, 1, 100, row=13, integer=True)

        # ── CFG Scale ──────────────────────────────────────────────────────────
        self._cfg_var = ctk.DoubleVar(value=7.5)
        _label(P, "CFG Scale", "7 = balanced · higher = stricter prompt", row=14)
        _slider_row(P, self._cfg_var, 1.0, 20.0, row=15, step=0.5, integer=False)

        _divider(P, row=16)

        # ── Seed & Batch ───────────────────────────────────────────────────────
        sb_row = ctk.CTkFrame(P, fg_color="transparent")
        sb_row.grid(row=17, column=0, padx=14, pady=(0, 10), sticky="ew")
        sb_row.grid_columnconfigure(0, weight=1)
        sb_row.grid_columnconfigure(2, weight=1)

        sc = ctk.CTkFrame(sb_row, fg_color="transparent")
        sc.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(sc, text="Seed", font=F_SM_B, text_color=TEXT_SEC).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(sc, text=" (−1 = random)", font=F_SM, text_color=TEXT_MUTED).grid(row=0, column=1, sticky="w")
        self._seed_var = ctk.StringVar(value="-1")
        ctk.CTkEntry(sc, textvariable=self._seed_var, width=96, height=30, font=F_MD,
                     fg_color=BG_INPUT, text_color=TEXT, border_color=BORDER, corner_radius=8
                     ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        bc = ctk.CTkFrame(sb_row, fg_color="transparent")
        bc.grid(row=0, column=2, sticky="e")
        ctk.CTkLabel(bc, text="Batch", font=F_SM_B, text_color=TEXT_SEC).grid(row=0, column=0, sticky="w")
        self._batch_var = ctk.IntVar(value=1)
        ctk.CTkEntry(bc, textvariable=self._batch_var, width=60, height=30, font=F_MD,
                     fg_color=BG_INPUT, text_color=TEXT, border_color=BORDER, corner_radius=8
                     ).grid(row=1, column=0, pady=(4, 0))

        # ── Extra widgets (injected by page) ───────────────────────────────────
        self._extra_row = 18
        if extra_fn:
            extra_fn(P, start_row=18)
            self._extra_row = 20   # rough offset

        # ── Generate button ────────────────────────────────────────────────────
        self._gen_btn = ctk.CTkButton(
            P, text="Generate", height=48, font=F_LG_B,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="#fff", corner_radius=8,
            command=self._clicked_generate,
        )
        self._gen_btn.grid(row=self._extra_row + 2, column=0, padx=14, pady=(10, 14), sticky="ew")

        self.grid_columnconfigure(0, weight=1)

    # ── Resolution helpers ────────────────────────────────────────────────────
    def _set_res(self, w: int, h: int):
        self._w_var.set(w)
        self._h_var.set(h)
        self._update_preset_buttons()

    def _update_preset_buttons(self):
        for btn, pw, ph in self._preset_btns:
            active = (self._w_var.get() == pw and self._h_var.get() == ph)
            btn.configure(
                fg_color=ACCENT if active else BG_CARD,
                hover_color=ACCENT_HOVER if active else BG_HOVER,
            )

    # ── Model loading ─────────────────────────────────────────────────────────
    def _load_models(self):
        def _fetch():
            try:
                models = list_models()
                data = [m.to_dict() for m in models]
            except Exception:
                data = []
            self.after(0, lambda: self._populate_models(data))
        threading.Thread(target=_fetch, daemon=True).start()

    def _populate_models(self, data: list):
        self._model_ids.clear()
        if not data:
            self._model_combo.configure(values=["No models installed"])
            self._model_combo.set("No models installed")
            return
        names = []
        for m in data:
            name = m.get("alias") or m.get("repo_id", "unknown")
            self._model_ids[name] = m.get("model_id", name)
            names.append(name)
        self._model_combo.configure(values=names)
        self._model_combo.set(names[0])

    # ── Generate callback ─────────────────────────────────────────────────────
    def _clicked_generate(self):
        if self._generating or not self._on_generate:
            return
        self._on_generate(self.get_params())

    # ── Public API ─────────────────────────────────────────────────────────────
    def get_params(self) -> dict:
        name = self._model_combo.get()
        return {
            "prompt":          self._prompt.get("0.0", "end").strip(),
            "negative_prompt": self._neg.get("0.0", "end").strip(),
            "model_id":        self._model_ids.get(name, name),
            "width":           int(self._w_var.get()),
            "height":          int(self._h_var.get()),
            "steps":           int(self._steps_var.get()),
            "cfg_scale":       round(self._cfg_var.get(), 1),
            "seed":            int(self._seed_var.get() or -1),
            "batch_size":      int(self._batch_var.get()),
        }

    def set_generating(self, generating: bool):
        self._generating = generating
        self._gen_btn.configure(
            text="Generating…" if generating else "Generate",
            state="disabled" if generating else "normal",
            fg_color=BG_HOVER if generating else ACCENT,
        )


# ── Small helpers ─────────────────────────────────────────────────────────────

def _label(parent, text: str, hint: str = "", row: int = 0):
    f = ctk.CTkFrame(parent, fg_color="transparent")
    f.grid(row=row, column=0, padx=14, pady=(10, 3), sticky="ew")
    ctk.CTkLabel(f, text=text, font=F_SM_B, text_color=TEXT_SEC).pack(side="left")
    if hint:
        ctk.CTkLabel(f, text=hint, font=F_SM, text_color=TEXT_MUTED).pack(side="left", padx=(8, 0))


def _lbl(parent, text: str):
    return ctk.CTkLabel(parent, text=text, font=F_SM, text_color=TEXT_MUTED)


def _divider(parent, row: int):
    ctk.CTkFrame(parent, height=1, fg_color=BORDER).grid(
        row=row, column=0, padx=14, pady=6, sticky="ew"
    )


def _spinbox(parent, var, lo: int, hi: int):
    e = ctk.CTkEntry(parent, textvariable=var, width=80, height=28, font=F_SM,
                     fg_color=BG_INPUT, text_color=TEXT,
                     border_color=BORDER, corner_radius=8)
    return e


def _slider_row(parent, var, lo, hi, row, step=1, integer=True):
    """Slider + live value label on a single grid row."""
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.grid(row=row, column=0, padx=14, pady=(0, 8), sticky="ew")
    frame.grid_columnconfigure(0, weight=1)

    val_lbl = ctk.CTkLabel(frame, text="", font=F_SM_B, text_color=ACCENT, width=40)
    val_lbl.grid(row=0, column=1, sticky="e")

    def _update(v):
        val_lbl.configure(text=str(int(float(v))) if integer else f"{float(v):.1f}")

    sl = ctk.CTkSlider(
        frame, variable=var, from_=lo, to=hi, number_of_steps=int((hi - lo) / step),
        fg_color=BG_INPUT, progress_color=ACCENT, button_color=ACCENT,
        button_hover_color=ACCENT_HOVER, command=_update,
    )
    sl.grid(row=0, column=0, sticky="ew")
    _update(var.get())
