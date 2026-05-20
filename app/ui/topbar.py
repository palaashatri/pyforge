"""Top status bar: page title + backend status pill."""
import customtkinter as ctk
from .theme import *


class TopBar(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        kw.setdefault("fg_color", BG_PANEL)
        kw.setdefault("corner_radius", 0)
        kw.setdefault("height", 54)
        super().__init__(parent, **kw)
        self.pack_propagate(False)
        self.grid_propagate(False)
        self._build()

    def _build(self):
        # Bottom border
        ctk.CTkFrame(self, height=1, fg_color=BORDER).pack(side="bottom", fill="x")

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20)

        self._title_lbl = ctk.CTkLabel(
            inner, text="Text to Image",
            font=F_LG_B, text_color=TEXT,
        )
        self._title_lbl.pack(side="left", pady=12)

        # Status pill
        self._pill = ctk.CTkFrame(inner, fg_color=BG_CARD,
                                  corner_radius=14, border_color=BORDER, border_width=1)
        self._pill.pack(side="right", pady=10)

        self._dot = ctk.CTkFrame(self._pill, width=8, height=8,
                                 corner_radius=4, fg_color=ACCENT)
        self._dot.pack(side="left", padx=(10, 0))

        self._status_lbl = ctk.CTkLabel(
            self._pill, text="Starting…", font=F_SM, text_color=TEXT_SEC,
        )
        self._status_lbl.pack(side="left", padx=(6, 12), pady=4)

    def set_title(self, title: str):
        self._title_lbl.configure(text=title)

    def set_status(self, text: str, ready: bool = False):
        colour = SUCCESS if ready else ACCENT
        self._dot.configure(fg_color=colour)
        self._status_lbl.configure(text=text, text_color=SUCCESS if ready else TEXT_SEC)
        self._pill.configure(border_color=blend_hex(colour, BG_CARD, 0.35))
