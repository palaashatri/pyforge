"""Slide-up toast notification that auto-dismisses."""
import customtkinter as ctk
from ..theme import *


class Toast:
    def __init__(self, root: ctk.CTk):
        self._root  = root
        self._after = None
        self._frame = ctk.CTkFrame(root, fg_color=BG_CARD, border_color=BORDER, border_width=1, corner_radius=10)
        self._label = ctk.CTkLabel(self._frame, text="", font=F_MD, text_color=TEXT, wraplength=460)
        self._label.pack(padx=18, pady=12)
        # Hidden by default — placed via place() when shown
        self._visible = False

    # ── Public ────────────────────────────────────────────────────────────────
    def show(self, message: str, kind: str = "error"):
        colour = {
            "error":   DANGER,
            "success": SUCCESS,
            "info":    ACCENT,
        }.get(kind, TEXT_SEC)

        self._frame.configure(border_color=colour)
        self._label.configure(text=message, text_color=colour)

        # Place above bottom-centre
        self._frame.place(relx=0.5, rely=1.0, anchor="s", y=-32)
        self._frame.lift()
        self._visible = True

        if self._after:
            self._root.after_cancel(self._after)
        self._after = self._root.after(4000, self._hide)

    def _hide(self):
        self._frame.place_forget()
        self._visible = False
