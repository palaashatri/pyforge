"""Text-to-Image page."""
import threading
import customtkinter as ctk

from ..theme import *
from ..components.prompt_panel import PromptPanel
from ..components.image_gallery import ImageGallery
from ...core.pipelines import generate_txt2img
from ...core.history import load_history, add_to_history


class TextToImagePage(ctk.CTkFrame):
    def __init__(self, parent, show_toast=None, **kw):
        kw.setdefault("fg_color", BG)
        super().__init__(parent, **kw)
        self._toast = show_toast
        self._build()
        self._load_history()

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._panel = PromptPanel(self, on_generate=self._generate, width=340)
        self._panel.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)

        right = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=12,
                             border_color=BORDER, border_width=1)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._gallery = ImageGallery(right, fg_color=BG_PANEL)
        self._gallery.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self._overlay = ctk.CTkLabel(right, text="", font=F_MD, text_color=TEXT_SEC)
        self._overlay.grid(row=1, column=0, pady=(0, 8))

    def _generate(self, params: dict):
        self._panel.set_generating(True)
        self._overlay.configure(text="Generating…")

        def _run():
            try:
                paths = generate_txt2img(
                    model_id        = params["model_id"],
                    prompt          = params["prompt"],
                    negative_prompt = params.get("negative_prompt", ""),
                    width           = params.get("width", 512),
                    height          = params.get("height", 512),
                    steps           = params.get("steps", 25),
                    cfg_scale       = params.get("cfg_scale", 7.5),
                    seed            = params.get("seed", -1),
                    batch_size      = params.get("batch_size", 1),
                )
                self.after(0, lambda: self._on_success(paths))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._on_error(err))

        threading.Thread(target=_run, daemon=True).start()

    def _on_success(self, paths: list):
        self._panel.set_generating(False)
        self._overlay.configure(text="")
        for p in paths:
            self._gallery.append_image(p)
        threading.Thread(target=add_to_history, args=(paths, "txt2img"), daemon=True).start()

    def _on_error(self, msg: str):
        self._panel.set_generating(False)
        self._overlay.configure(text="")
        if self._toast:
            self._toast(msg, "error")

    def _load_history(self):
        def _run():
            try:
                paths = [h["path"] for h in load_history() if h.get("page") == "txt2img"]
                self.after(0, lambda: self._gallery.set_images(paths))
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()
