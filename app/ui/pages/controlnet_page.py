"""ControlNet page.

Generate images guided by a control image (Canny, Depth, Pose, etc.).
"""
import threading
import customtkinter as ctk
from tkinter import filedialog

from ..theme import *
from ..components.image_gallery import ImageGallery
from ...core.pipelines import generate_controlnet
from ...core.manager import list_models
from ...core.history import load_history, add_to_history


class ControlNetPage(ctk.CTkFrame):
    def __init__(self, parent, show_toast=None, **kw):
        kw.setdefault("fg_color", BG)
        super().__init__(parent, **kw)
        self._toast = show_toast
        self._control_path = ""
        self._model_ids = {}
        self._build()
        self._load_models()
        self._load_history()

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(self, width=320, fg_color=BG_PANEL, corner_radius=12,
                                       border_color=BORDER, border_width=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="ControlNet", font=F_MD_B, text_color=TEXT).grid(
            row=0, column=0, padx=14, pady=(14, 8), sticky="w")

        ctk.CTkLabel(left, text="Model", font=F_SM_B, text_color=TEXT_SEC).grid(
            row=1, column=0, padx=14, pady=(8, 2), sticky="w")
        self._model_var = ctk.StringVar()
        self._model_menu = ctk.CTkOptionMenu(left, variable=self._model_var, values=["Loading…"])
        self._model_menu.grid(row=2, column=0, padx=14, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(left, text="Control type", font=F_SM_B, text_color=TEXT_SEC).grid(
            row=3, column=0, padx=14, pady=(8, 2), sticky="w")
        self._type_var = ctk.StringVar(value="canny")
        ctk.CTkOptionMenu(left, variable=self._type_var,
                          values=["canny", "depth", "pose", "scribble", "segmentation", "normal map"]).grid(
            row=4, column=0, padx=14, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(left, text="Prompt", font=F_SM_B, text_color=TEXT_SEC).grid(
            row=5, column=0, padx=14, pady=(8, 2), sticky="w")
        self._prompt = ctk.CTkTextbox(left, height=80, font=F_SM)
        self._prompt.grid(row=6, column=0, padx=14, pady=(0, 8), sticky="ew")

        ctk.CTkButton(left, text="Load Control Image", command=self._load_control).grid(
            row=7, column=0, padx=14, pady=8, sticky="ew")

        self._gen_btn = ctk.CTkButton(left, text="Generate", command=self._generate,
                                      fg_color=ACCENT, hover_color=ACCENT_HOVER)
        self._gen_btn.grid(row=8, column=0, padx=14, pady=8, sticky="ew")

        right = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=12,
                             border_color=BORDER, border_width=1)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._gallery = ImageGallery(right, fg_color=BG_PANEL)
        self._gallery.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self._status = ctk.CTkLabel(right, text="Load a control image", font=F_SM, text_color=TEXT_MUTED)
        self._status.grid(row=1, column=0, pady=8)

    def _load_control(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")])
        if path:
            self._control_path = path
            self._status.configure(text=f"Control: {path.split('/')[-1]}")

    def _generate(self):
        if not self._control_path:
            if self._toast:
                self._toast("Load a control image first", "error")
            return
        model_id = self._model_var.get()
        if not model_id or model_id == "Loading…":
            return
        prompt = self._prompt.get("1.0", "end").strip()
        self._gen_btn.configure(state="disabled", text="Generating…")

        def _run():
            try:
                paths = generate_controlnet(
                    model_id=model_id,
                    prompt=prompt,
                    control_image_path=self._control_path,
                    controlnet_type=self._type_var.get(),
                )
                self.after(0, lambda: self._on_success(paths))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=_run, daemon=True).start()

    def _on_success(self, paths):
        self._gen_btn.configure(state="normal", text="Generate")
        for p in paths:
            self._gallery.append_image(p)
        threading.Thread(target=add_to_history, args=(paths, "controlnet"), daemon=True).start()

    def _on_error(self, msg):
        self._gen_btn.configure(state="normal", text="Generate")
        if self._toast:
            self._toast(msg, "error")

    def _load_models(self):
        def _run():
            try:
                models = list_models()
                names = [m.get("name", m.get("id", "?")) for m in models]
                self.after(0, lambda: self._set_models(names))
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()

    def _set_models(self, names):
        if names:
            self._model_menu.configure(values=names)
            self._model_var.set(names[0])

    def _load_history(self):
        def _run():
            try:
                paths = [h["path"] for h in load_history() if h.get("page") == "controlnet"]
                self.after(0, lambda: self._gallery.set_images(paths))
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()
