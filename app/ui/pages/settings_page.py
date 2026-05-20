"""Settings page."""
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

    # ── Load / Save ───────────────────────────────────────────────────────────
    def _load_settings(self):
        d = config.as_dict()
        self._device_var.set(d.get("device", "auto"))
        self._xformers_var.set(d.get("xformers", False))
        self._format_var.set(d.get("image_format", "png").lower())
        self._outdir_var.set(d.get("outputs_dir", ""))
        self._theme_var.set(d.get("theme", "dark"))

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
