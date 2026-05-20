"""Scrollable image gallery with hover actions."""
import os
import threading
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk

from ..theme import *


_THUMB = 168   # thumbnail size in px
_COLS  = 3     # default columns


class ImageGallery(ctk.CTkScrollableFrame):
    def __init__(self, parent, on_use_as_input=None, **kw):
        kw.setdefault("fg_color", BG_PANEL)
        kw.setdefault("scrollbar_button_color", BG_HOVER)
        super().__init__(parent, **kw)
        self._paths: list[str] = []
        self._refs:  list      = []   # keep PhotoImage refs alive
        self._on_use = on_use_as_input
        self._detail_win = None
        self.grid_columnconfigure(tuple(range(_COLS)), weight=1, uniform="col")

    # ── Public API ────────────────────────────────────────────────────────────
    def set_images(self, paths: list[str]):
        self._paths = list(paths)
        self._refs.clear()
        for w in self.winfo_children():
            w.destroy()
        self._render()

    def append_image(self, path: str):
        self._paths.append(path)
        idx = len(self._paths) - 1
        r, c = divmod(idx, _COLS)
        self._add_tile(path, idx, r, c)

    # ── Internals ─────────────────────────────────────────────────────────────
    def _render(self):
        for i, p in enumerate(self._paths):
            r, c = divmod(i, _COLS)
            self._add_tile(p, i, r, c)

        if not self._paths:
            self._empty_state()

    def _empty_state(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.grid(row=0, column=0, columnspan=_COLS, pady=60)
        ctk.CTkLabel(f, text="◇", font=(FONT_FACE, 48), text_color=TEXT_MUTED).pack()
        ctk.CTkLabel(f, text="Generated images appear here", font=F_MD, text_color=TEXT_MUTED).pack(pady=(6, 2))
        ctk.CTkLabel(f, text="Enter a prompt and click Generate", font=F_SM, text_color=TEXT_MUTED).pack()

    def _add_tile(self, path: str, idx: int, row: int, col: int):
        tile = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        tile.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        # Load thumbnail in bg thread to avoid UI stutter
        def _load():
            try:
                img = Image.open(path)
                img.thumbnail((_THUMB, _THUMB), Image.LANCZOS)
                ctk_img = ctk.CTkImage(img, size=img.size)
                self.after(0, lambda: _place(ctk_img, img.size))
            except Exception:
                pass

        def _place(ctk_img, size):
            lbl = ctk.CTkLabel(tile, image=ctk_img, text="", cursor="hand2")
            lbl.pack(padx=6, pady=6)
            self._refs.append(ctk_img)
            lbl.bind("<Button-1>", lambda e: self._open_detail(path))

            # Action row
            act = ctk.CTkFrame(tile, fg_color="transparent")
            act.pack(fill="x", padx=6, pady=(0, 6))
            _btn(act, "Save…",      lambda: self._save(path))
            _btn(act, "Folder",     lambda: self._reveal(path))
            if self._on_use:
                _btn(act, "Use as Input", lambda: self._on_use(path))

        threading.Thread(target=_load, daemon=True).start()

    # ── Actions ───────────────────────────────────────────────────────────────
    def _save(self, path: str):
        from tkinter import filedialog
        dst = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("All", "*.*")],
            initialfile=os.path.basename(path),
        )
        if dst:
            import shutil
            shutil.copy2(path, dst)

    def _reveal(self, path: str):
        import subprocess, sys
        folder = os.path.dirname(path)
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        else:
            subprocess.Popen(["xdg-open", folder])

    def _open_detail(self, path: str):
        if self._detail_win and self._detail_win.winfo_exists():
            self._detail_win.destroy()
        win = ctk.CTkToplevel(self)
        win.title("Image")
        win.configure(fg_color=BG_CARD)
        self._detail_win = win
        try:
            img = Image.open(path)
            img.thumbnail((900, 900), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            win.geometry(f"{img.width}x{img.height}")
            lbl = tk.Label(win, image=photo, bg=BG_CARD)
            lbl.image = photo
            lbl.pack()
        except Exception as e:
            ctk.CTkLabel(win, text=str(e), text_color=DANGER).pack(padx=20, pady=20)


def _btn(parent, text, cmd):
    ctk.CTkButton(
        parent, text=text, command=cmd,
        height=24, font=F_SM,
        fg_color=BG_HOVER, hover_color=BG_INPUT,
        text_color=TEXT_SEC, corner_radius=6,
    ).pack(side="left", padx=2)
