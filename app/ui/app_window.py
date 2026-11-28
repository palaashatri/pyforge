"""Main application window."""
import threading
import customtkinter as ctk

from .theme import *
from .sidebar import Sidebar
from .topbar import TopBar
from .components.toast import Toast
from .pages.txt2img_page import TextToImagePage
from .pages.img2img_page import ImageToImagePage
from .pages.inpaint_page import InpaintPage
from .pages.controlnet_page import ControlNetPage
from .pages.models_page import ModelsPage
from .pages.settings_page import SettingsPage

_PAGES = [
    ("Text to Image",  TextToImagePage),
    ("Image to Image", ImageToImagePage),
    ("Inpainting",     InpaintPage),
    ("ControlNet",     ControlNetPage),
    ("Models",         ModelsPage),
    ("Settings",       SettingsPage),
]

_PAGE_TITLES = [p[0] for p in _PAGES]
_GEN_PAGE_INDICES = {0, 1}   # pages that need models to work


class AppWindow(ctk.CTk):
    def __init__(self):
        from app.core.config import config as _cfg
        # set_appearance_mode MUST be called before super().__init__() so that
        # CTk builds the root window with the correct theme from the start.
        ctk.set_appearance_mode(_cfg.theme)
        ctk.set_default_color_theme("blue")

        super().__init__(fg_color=BG)

        self.title("PyForge Studio")
        self.geometry("1280x820")
        self.minsize(900, 600)

        self._setup_grid()
        self._build_sidebar()
        self._build_topbar()
        self._build_pages()

        self._toast = Toast(self)
        self._switch_page(0)

    # ── Layout ────────────────────────────────────────────────────────────────
    def _setup_grid(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

    def _build_sidebar(self):
        self._sidebar = Sidebar(self, navigate_cmd=self._switch_page)
        self._sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")

    def _build_topbar(self):
        self._topbar = TopBar(self)
        self._topbar.grid(row=0, column=1, sticky="ew")

    def _build_pages(self):
        self._container = ctk.CTkFrame(self, fg_color=BG)
        self._container.grid(row=1, column=1, sticky="nsew")
        self._container.grid_columnconfigure(0, weight=1)
        self._container.grid_rowconfigure(0, weight=1)

        self._pages: list[ctk.CTkFrame] = []
        for _, PageClass in _PAGES:
            page = PageClass(self._container, show_toast=self._show_toast)
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_remove()
            self._pages.append(page)

        self._current_idx = -1

    # ── Navigation ────────────────────────────────────────────────────────────
    def _switch_page(self, idx: int):
        if idx == self._current_idx:
            return
        if 0 <= self._current_idx < len(self._pages):
            self._pages[self._current_idx].grid_remove()
        self._pages[idx].grid()
        self._current_idx = idx
        self._sidebar.set_selected(idx)
        self._topbar.set_title(_PAGE_TITLES[idx])

        if idx in _GEN_PAGE_INDICES:
            self._topbar.set_status("Checking…", ready=False)
            threading.Thread(target=self._check_models_status, daemon=True).start()
        else:
            self._topbar.set_status("Ready", ready=True)

    def _check_models_status(self):
        try:
            from app.core.manager import list_models
            has_models = bool(list_models())
        except Exception:
            has_models = False
        if has_models:
            self.after(0, lambda: self._topbar.set_status("Ready", ready=True))
        else:
            self.after(0, lambda: self._topbar.set_status(
                "No models installed — go to Models to download", ready=False))

    # ── Toast ─────────────────────────────────────────────────────────────────
    def _show_toast(self, message: str, kind: str = "info"):
        self._toast.show(message, kind)
