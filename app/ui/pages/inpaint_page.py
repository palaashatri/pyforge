"""Inpainting page.

Load an image, paint a mask, and regenerate the masked region.
"""
import threading
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image, ImageDraw

from ..theme import *
from ..components.image_gallery import ImageGallery
from ...core.pipelines import generate_inpaint
from ...core.manager import list_models
from ...core.history import load_history, add_to_history


class InpaintPage(ctk.CTkFrame):
    def __init__(self, parent, show_toast=None, **kw):
        kw.setdefault("fg_color", BG)
        super().__init__(parent, **kw)
        self._toast = show_toast
        self._input_path = ""
        self._mask = None
        self._drawing = False
        self._photo_ref = None
        self._model_ids = {}
        self._build()
        self._load_models()
        self._load_history()

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left panel
        left = ctk.CTkScrollableFrame(self, width=320, fg_color=BG_PANEL, corner_radius=12,
                                       border_color=BORDER, border_width=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Inpainting", font=F_MD_B, text_color=TEXT).grid(
            row=0, column=0, padx=14, pady=(14, 8), sticky="w")

        # Model selector
        ctk.CTkLabel(left, text="Model", font=F_SM_B, text_color=TEXT_SEC).grid(
            row=1, column=0, padx=14, pady=(8, 2), sticky="w")
        self._model_var = ctk.StringVar()
        self._model_menu = ctk.CTkOptionMenu(left, variable=self._model_var, values=["Loading…"])
        self._model_menu.grid(row=2, column=0, padx=14, pady=(0, 8), sticky="ew")

        # Prompt
        ctk.CTkLabel(left, text="Prompt", font=F_SM_B, text_color=TEXT_SEC).grid(
            row=3, column=0, padx=14, pady=(8, 2), sticky="w")
        self._prompt = ctk.CTkTextbox(left, height=80, font=F_SM)
        self._prompt.grid(row=4, column=0, padx=14, pady=(0, 8), sticky="ew")

        # Load image button
        ctk.CTkButton(left, text="Load Image", command=self._load_image).grid(
            row=5, column=0, padx=14, pady=8, sticky="ew")

        # Generate
        self._gen_btn = ctk.CTkButton(left, text="Generate", command=self._generate,
                                      fg_color=ACCENT, hover_color=ACCENT_HOVER)
        self._gen_btn.grid(row=6, column=0, padx=14, pady=8, sticky="ew")

        # Right panel: canvas for drawing mask + gallery
        right = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=12,
                             border_color=BORDER, border_width=1)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._canvas = ctk.CTkCanvas(right, bg="#1a1a1a", highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self._canvas.bind("<ButtonPress-1>", self._start_draw)
        self._canvas.bind("<B1-Motion>", self._draw)
        self._canvas.bind("<ButtonRelease-1>", self._end_draw)

        self._gallery = ImageGallery(right, fg_color=BG_PANEL)
        self._gallery.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        self._overlay = ctk.CTkLabel(right, text="Load an image and paint the mask (white = regenerate)",
                                     font=F_SM, text_color=TEXT_MUTED)
        self._overlay.grid(row=0, column=0, pady=20)

    def _load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")])
        if not path:
            return
        self._input_path = path
        img = Image.open(path).convert("RGB")
        self._mask = Image.new("L", img.size, 0)
        self._draw_mask = ImageDraw.Draw(self._mask)
        # Display scaled
        self._display_img(img)
        self._overlay.grid_remove()

    def _display_img(self, img: Image.Image):
        # Simple display; in production scale to canvas
        self._photo_ref = ctk.CTkImage(img, size=(400, 400))
        # For canvas we use PhotoImage if needed; simplified here
        self._canvas.delete("all")
        self._canvas.create_text(200, 200, text="Image loaded\nPaint mask with mouse", fill="white")

    def _start_draw(self, event):
        self._drawing = True
        self._last = (event.x, event.y)

    def _draw(self, event):
        if not self._drawing or not self._mask:
            return
        # Simplified: draw on mask (coords need mapping in real impl)
        self._draw_mask.ellipse([event.x-10, event.y-10, event.x+10, event.y+10], fill=255)
        self._canvas.create_oval(event.x-10, event.y-10, event.x+10, event.y+10, outline="red", width=2)

    def _end_draw(self, event):
        self._drawing = False

    def _generate(self):
        if not self._input_path or not self._mask:
            if self._toast:
                self._toast("Load an image and paint a mask first", "error")
            return
        model_id = self._model_var.get()
        if not model_id or model_id == "Loading…":
            if self._toast:
                self._toast("Select a model", "error")
            return
        prompt = self._prompt.get("1.0", "end").strip()
        self._gen_btn.configure(state="disabled", text="Generating…")

        def _run():
            try:
                # Save temp mask
                mask_path = "/tmp/inpaint_mask.png"
                self._mask.save(mask_path)
                paths = generate_inpaint(
                    model_id=model_id,
                    prompt=prompt,
                    input_image_path=self._input_path,
                    mask_image_path=mask_path,
                )
                self.after(0, lambda: self._on_success(paths))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=_run, daemon=True).start()

    def _on_success(self, paths):
        self._gen_btn.configure(state="normal", text="Generate")
        for p in paths:
            self._gallery.append_image(p)
        threading.Thread(target=add_to_history, args=(paths, "inpaint"), daemon=True).start()

    def _on_error(self, msg):
        self._gen_btn.configure(state="normal", text="Generate")
        if self._toast:
            self._toast(msg, "error")

    def _load_models(self):
        def _run():
            try:
                models = list_models()
                names = [m.get("name", m.get("id", "?")) for m in models]
                ids = {m.get("name", m.get("id")): m.get("id") for m in models}
                self.after(0, lambda: self._set_models(names, ids))
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()

    def _set_models(self, names, ids):
        self._model_ids = ids
        if names:
            self._model_menu.configure(values=names)
            self._model_var.set(names[0])

    def _load_history(self):
        def _run():
            try:
                paths = [h["path"] for h in load_history() if h.get("page") == "inpaint"]
                self.after(0, lambda: self._gallery.set_images(paths))
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()
