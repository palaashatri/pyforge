"""Navigation sidebar."""
import customtkinter as ctk
from .theme import *


_NAV = [
    # (label, section-header-or-None)
    ("Text to Image",  "GENERATE"),
    ("Image to Image", None),
    ("Models",         "LIBRARY"),
    ("Settings",       None),
]


class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, navigate_cmd, **kw):
        kw.setdefault("fg_color", BG_SIDEBAR)
        kw.setdefault("corner_radius", 0)
        kw.setdefault("width", 210)
        super().__init__(parent, **kw)
        self._navigate = navigate_cmd
        self._buttons: list[ctk.CTkButton] = []
        self._selected = -1
        self._build()

    def _build(self):
        self.grid_propagate(False)

        # ── Logo ──────────────────────────────────────────────────────────────
        logo_frame = ctk.CTkFrame(self, fg_color="transparent", height=68)
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)
        logo_inner = ctk.CTkFrame(logo_frame, fg_color="transparent")
        logo_inner.place(relx=0, rely=0.5, anchor="w", x=18)

        gem = ctk.CTkFrame(logo_inner, width=32, height=32, corner_radius=8,
                           fg_color=ACCENT)
        gem.pack(side="left")
        gem.pack_propagate(False)
        ctk.CTkLabel(gem, text="◆", font=(FONT_FACE, 14), text_color="#fff").place(relx=0.5, rely=0.5, anchor="center")

        txt = ctk.CTkFrame(logo_inner, fg_color="transparent")
        txt.pack(side="left", padx=(10, 0))
        ctk.CTkLabel(txt, text="PyForge", font=F_MD_B, text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(txt, text="Studio",  font=F_SM,   text_color=TEXT_MUTED).pack(anchor="w")

        # ── Separator ─────────────────────────────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color=BORDER).pack(fill="x")

        # ── Nav items ─────────────────────────────────────────────────────────
        nav_container = ctk.CTkFrame(self, fg_color="transparent")
        nav_container.pack(fill="both", expand=True, padx=8, pady=4)

        idx = 0
        for label, section in _NAV:
            if section:
                ctk.CTkLabel(
                    nav_container, text=section, font=(FONT_FACE, 10, "bold"),
                    text_color=TEXT_MUTED,
                ).pack(anchor="w", padx=12, pady=(16, 4))

            btn = ctk.CTkButton(
                nav_container,
                text=f"   {label}",
                anchor="w",
                height=40,
                font=F_MD,
                fg_color="transparent",
                hover_color=BG_HOVER,
                text_color=TEXT_SEC,
                corner_radius=8,
                command=lambda i=idx: self._navigate(i),
            )
            btn.pack(fill="x", pady=1)
            self._buttons.append(btn)
            idx += 1

        # ── Footer ────────────────────────────────────────────────────────────
        ctk.CTkLabel(self, text="v1.0.0", font=F_SM, text_color=TEXT_MUTED).pack(pady=10)

        self.set_selected(0)

    def set_selected(self, index: int):
        if self._selected == index:
            return
        # Deselect old
        if 0 <= self._selected < len(self._buttons):
            self._buttons[self._selected].configure(
                fg_color="transparent", text_color=TEXT_SEC,
                font=F_MD,
            )
        # Select new
        self._selected = index
        if 0 <= index < len(self._buttons):
            self._buttons[index].configure(
                fg_color=ACCENT_TINT,
                text_color=TEXT,
                font=F_MD_B,
            )
