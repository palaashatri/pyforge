"""Image-to-Image page.

Two modes, toggled at the top of the left panel:
  - Transform  — classic img2img with a denoising strength slider
  - Upscale    — enlarge an image with a continuous scale slider (1× – 8×)

The right panel is split: top half shows the selected input image as a live
preview; bottom half is the output gallery (shared by both modes).
"""
import threading
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image

from ..theme import *
from ..components.image_gallery import ImageGallery
from ...core.pipelines import generate_img2img, generate_upscale
from ...core.manager import list_models
from ...core.history import load_history, add_to_history


# ── Small layout helpers (private to this file) ───────────────────────────────

def _lbl(parent, text, hint="", row=0):
    f = ctk.CTkFrame(parent, fg_color="transparent")
    f.grid(row=row, column=0, padx=14, pady=(10, 3), sticky="ew")
    ctk.CTkLabel(f, text=text, font=F_SM_B, text_color=TEXT_SEC).pack(side="left")
    if hint:
        ctk.CTkLabel(f, text=hint, font=F_SM, text_color=TEXT_MUTED).pack(side="left", padx=(6, 0))


def _div(parent, row):
    ctk.CTkFrame(parent, height=1, fg_color=BORDER).grid(
        row=row, column=0, padx=14, pady=6, sticky="ew")


def _slider(parent, var, lo, hi, row, step=1, integer=True):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.grid(row=row, column=0, padx=14, pady=(0, 8), sticky="ew")
    frame.grid_columnconfigure(0, weight=1)
    val_lbl = ctk.CTkLabel(frame, text="", font=F_SM_B, text_color=ACCENT, width=46)
    val_lbl.grid(row=0, column=1, sticky="e")

    def _upd(v):
        val_lbl.configure(text=str(int(float(v))) if integer else f"{float(v):.2f}")

    steps = max(1, int((hi - lo) / step))
    ctk.CTkSlider(
        frame, variable=var, from_=lo, to=hi, number_of_steps=steps,
        fg_color=BG_INPUT, progress_color=ACCENT,
        button_color=ACCENT, button_hover_color=ACCENT_HOVER,
        command=_upd,
    ).grid(row=0, column=0, sticky="ew")
    _upd(var.get())


# ── Page ──────────────────────────────────────────────────────────────────────

class ImageToImagePage(ctk.CTkFrame):
    def __init__(self, parent, show_toast=None, **kw):
        kw.setdefault("fg_color", BG)
        super().__init__(parent, **kw)
        self._toast       = show_toast
        self._input_path  = ""
        self._mode        = "transform"   # "transform" | "upscale"
        self._photo_ref   = None          # keeps CTkImage alive
        self._model_ids: dict[str, str] = {}
        self._build()
        self._load_models()
        self._load_history()

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_left()
        self._build_right()

    def _build_left(self):
        left = ctk.CTkScrollableFrame(
            self, width=320, fg_color=BG_PANEL,
            corner_radius=12, border_color=BORDER, border_width=1,
            scrollbar_button_color=BG_HOVER,
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        left.grid_columnconfigure(0, weight=1)

        # ── Mode toggle ───────────────────────────────────────────────────────
        tog = ctk.CTkFrame(left, fg_color=BG_INPUT, corner_radius=10)
        tog.grid(row=0, column=0, padx=14, pady=(14, 4), sticky="ew")
        tog.grid_columnconfigure(0, weight=1)
        tog.grid_columnconfigure(1, weight=1)

        self._tx_btn = ctk.CTkButton(
            tog, text="Transform", height=34, font=F_SM_B,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#fff",
            corner_radius=8, command=lambda: self._set_mode("transform"),
        )
        self._tx_btn.grid(row=0, column=0, padx=4, pady=4, sticky="ew")

        self._up_btn = ctk.CTkButton(
            tog, text="Upscale", height=34, font=F_SM_B,
            fg_color="transparent", hover_color=BG_HOVER, text_color=TEXT_MUTED,
            corner_radius=8, command=lambda: self._set_mode("upscale"),
        )
        self._up_btn.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

        # ── Image picker ──────────────────────────────────────────────────────
        _div(left, row=1)
        _lbl(left, "Input Image", row=2)

        pick = ctk.CTkFrame(left, fg_color="transparent")
        pick.grid(row=3, column=0, padx=14, pady=(0, 4), sticky="ew")
        pick.grid_columnconfigure(0, weight=1)

        self._img_lbl = ctk.CTkLabel(
            pick, text="No image selected", font=F_SM, text_color=TEXT_MUTED,
        )
        self._img_lbl.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            pick, text="Browse…", width=90, height=28, font=F_SM,
            fg_color=BG_CARD, hover_color=BG_HOVER, text_color=TEXT_SEC,
            corner_radius=8, command=self._pick_image,
        ).grid(row=0, column=1, padx=(6, 0))

        # ── Model selector (shared) ───────────────────────────────────────────
        _div(left, row=4)
        _lbl(left, "Model", row=5)

        mrow = ctk.CTkFrame(left, fg_color="transparent")
        mrow.grid(row=6, column=0, padx=14, pady=(0, 4), sticky="ew")
        mrow.grid_columnconfigure(0, weight=1)

        self._model_combo = ctk.CTkComboBox(
            mrow, values=["Loading…"], font=F_MD,
            fg_color=BG_INPUT, text_color=TEXT,
            border_color=BORDER, button_color=BG_HOVER,
            dropdown_fg_color=BG_CARD, corner_radius=8,
        )
        self._model_combo.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            mrow, text="R", width=34, height=34, font=F_SM_B,
            fg_color=BG_CARD, hover_color=BG_HOVER, text_color=TEXT_SEC,
            corner_radius=8, command=self._load_models,
        ).grid(row=0, column=1, padx=(6, 0))

        _div(left, row=7)

        # ── Transform controls ────────────────────────────────────────────────
        self._tx_frame = ctk.CTkFrame(left, fg_color="transparent")
        self._tx_frame.grid(row=8, column=0, sticky="ew")
        self._tx_frame.grid_columnconfigure(0, weight=1)
        self._build_transform(self._tx_frame)

        # ── Upscale controls ──────────────────────────────────────────────────
        self._up_frame = ctk.CTkFrame(left, fg_color="transparent")
        self._up_frame.grid(row=8, column=0, sticky="ew")
        self._up_frame.grid_columnconfigure(0, weight=1)
        self._build_upscale(self._up_frame)
        self._up_frame.grid_remove()          # hidden until Upscale mode

    def _build_transform(self, p):
        _lbl(p, "Strength", "0 = keep original · 1 = fully redraw", row=0)
        self._strength_var = ctk.DoubleVar(value=0.75)
        _slider(p, self._strength_var, 0.0, 1.0, row=1, step=0.05, integer=False)

        _div(p, row=2)

        _lbl(p, "Prompt", row=3)
        self._prompt = ctk.CTkTextbox(
            p, height=72, font=F_MD,
            fg_color=BG_INPUT, text_color=TEXT,
            border_color=BORDER, border_width=1, corner_radius=8,
        )
        self._prompt.grid(row=4, column=0, padx=14, pady=(0, 8), sticky="ew")
        self._prompt.bind("<FocusIn>",
                          lambda e: self._prompt.configure(border_color=ACCENT))
        self._prompt.bind("<FocusOut>",
                          lambda e: self._prompt.configure(border_color=BORDER))

        _lbl(p, "Avoid", row=5)
        self._neg = ctk.CTkTextbox(
            p, height=44, font=F_MD,
            fg_color=BG_INPUT, text_color=TEXT,
            border_color=BORDER, border_width=1, corner_radius=8,
        )
        self._neg.grid(row=6, column=0, padx=14, pady=(0, 8), sticky="ew")

        _div(p, row=7)

        self._steps_var = ctk.DoubleVar(value=25)
        _lbl(p, "Steps", row=8)
        _slider(p, self._steps_var, 1, 100, row=9, integer=True)

        self._cfg_var = ctk.DoubleVar(value=7.5)
        _lbl(p, "CFG Scale", row=10)
        _slider(p, self._cfg_var, 1.0, 20.0, row=11, step=0.5, integer=False)

        _div(p, row=12)

        _lbl(p, "Seed", "(-1 = random)", row=13)
        self._seed_var = ctk.StringVar(value="-1")
        ctk.CTkEntry(
            p, textvariable=self._seed_var, height=30, font=F_MD,
            fg_color=BG_INPUT, text_color=TEXT,
            border_color=BORDER, corner_radius=8,
        ).grid(row=14, column=0, padx=14, pady=(0, 8), sticky="ew")

        self._gen_btn = ctk.CTkButton(
            p, text="Generate", height=48, font=F_LG_B,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#fff",
            corner_radius=8, command=self._generate,
        )
        self._gen_btn.grid(row=15, column=0, padx=14, pady=(6, 14), sticky="ew")

    def _build_upscale(self, p):
        _lbl(p, "Scale Factor", "drag to choose any enlargement", row=0)
        self._scale_var = ctk.DoubleVar(value=2.0)
        _slider(p, self._scale_var, 1.0, 8.0, row=1, step=0.25, integer=False)

        _div(p, row=2)

        self._up_btn_go = ctk.CTkButton(
            p, text="Upscale", height=48, font=F_LG_B,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#fff",
            corner_radius=8, command=self._upscale,
        )
        self._up_btn_go.grid(row=3, column=0, padx=14, pady=(6, 14), sticky="ew")

    def _build_right(self):
        right = ctk.CTkFrame(
            self, fg_color=BG_PANEL, corner_radius=12,
            border_color=BORDER, border_width=1,
        )
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=2)   # preview gets less space
        right.grid_rowconfigure(1, weight=3)   # gallery gets more

        # Input preview
        preview_wrap = ctk.CTkFrame(right, fg_color=BG_CARD, corner_radius=8)
        preview_wrap.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 4))
        preview_wrap.grid_rowconfigure(0, weight=1)
        preview_wrap.grid_columnconfigure(0, weight=1)

        self._preview = ctk.CTkLabel(
            preview_wrap,
            text="Click here or use Browse to pick an input image",
            font=F_MD, text_color=TEXT_MUTED, cursor="hand2",
        )
        self._preview.grid(row=0, column=0, sticky="nsew")
        self._preview.bind("<Button-1>", lambda _e: self._pick_image())

        # Output gallery
        self._gallery = ImageGallery(
            right, fg_color=BG_PANEL, on_use_as_input=self._set_input,
        )
        self._gallery.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 4))

        self._overlay = ctk.CTkLabel(
            right, text="", font=F_MD, text_color=TEXT_SEC,
        )
        self._overlay.grid(row=2, column=0, pady=(0, 6))

    # ── Mode switching ────────────────────────────────────────────────────────
    def _set_mode(self, mode: str):
        self._mode = mode
        if mode == "transform":
            self._tx_btn.configure(
                fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#fff")
            self._up_btn.configure(
                fg_color="transparent", hover_color=BG_HOVER, text_color=TEXT_MUTED)
            self._up_frame.grid_remove()
            self._tx_frame.grid()
        else:
            self._up_btn.configure(
                fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#fff")
            self._tx_btn.configure(
                fg_color="transparent", hover_color=BG_HOVER, text_color=TEXT_MUTED)
            self._tx_frame.grid_remove()
            self._up_frame.grid()

    # ── Image picking ─────────────────────────────────────────────────────────
    def _pick_image(self):
        p = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All", "*.*")]
        )
        if p:
            self._set_input(p)

    def _set_input(self, path: str):
        self._input_path = path
        short = path if len(path) < 44 else "…" + path[-42:]
        self._img_lbl.configure(text=short, text_color=TEXT_SEC)

        # Live preview on the right panel
        try:
            img = Image.open(path)
            # Thumbnail within 600×260 (right-panel preview area, rough estimate)
            img.thumbnail((600, 260), Image.LANCZOS)
            ctk_img = ctk.CTkImage(img, size=img.size)
            self._preview.configure(image=ctk_img, text="")
            self._photo_ref = ctk_img   # prevent GC
        except Exception:
            self._preview.configure(image=None, text=short)

    # ── Model loading ─────────────────────────────────────────────────────────
    def _load_models(self):
        def _run():
            try:
                models = list_models()
                data = [m.to_dict() for m in models]
            except Exception:
                data = []
            self.after(0, lambda: self._populate_models(data))
        threading.Thread(target=_run, daemon=True).start()

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

    # ── Generate (Transform mode) ─────────────────────────────────────────────
    def _generate(self):
        if not self._input_path:
            if self._toast:
                self._toast("Pick an input image first.", "info")
            return
        name = self._model_combo.get()
        if name in ("No models installed", "Loading…"):
            if self._toast:
                self._toast("Download a model from the Models page first.", "info")
            return

        self._gen_btn.configure(
            text="Generating…", state="disabled", fg_color=BG_HOVER)
        self._overlay.configure(text="Generating…")

        model_id = self._model_ids.get(name, name)
        prompt   = self._prompt.get("0.0", "end").strip()
        neg      = self._neg.get("0.0", "end").strip()
        strength = round(self._strength_var.get(), 2)
        steps    = int(self._steps_var.get())
        cfg      = round(self._cfg_var.get(), 1)
        seed     = int(self._seed_var.get() or -1)
        path     = self._input_path

        def _run():
            try:
                paths = generate_img2img(
                    model_id=model_id, prompt=prompt,
                    input_image_path=path, negative_prompt=neg,
                    strength=strength, steps=steps, cfg_scale=cfg, seed=seed,
                )
                self.after(0, lambda: self._on_done(paths, "img2img"))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._on_error(err, "transform"))

        threading.Thread(target=_run, daemon=True).start()

    # ── Upscale ───────────────────────────────────────────────────────────────
    def _upscale(self):
        if not self._input_path:
            if self._toast:
                self._toast("Pick an input image first.", "info")
            return
        name = self._model_combo.get()
        if name in ("No models installed", "Loading…"):
            if self._toast:
                self._toast("Download a model from the Models page first.", "info")
            return

        self._up_btn_go.configure(
            text="Upscaling…", state="disabled", fg_color=BG_HOVER)
        self._overlay.configure(text="Upscaling…")

        model_id = self._model_ids.get(name, name)
        scale    = round(self._scale_var.get(), 2)
        path     = self._input_path

        def _run():
            try:
                paths = generate_upscale(
                    model_id=model_id,
                    input_image_path=path,
                    scale_factor=scale,
                )
                self.after(0, lambda: self._on_done(paths, "upscale"))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._on_error(err, "upscale"))

        threading.Thread(target=_run, daemon=True).start()

    # ── Shared callbacks ──────────────────────────────────────────────────────
    def _on_done(self, paths: list, page: str):
        self._overlay.configure(text="")
        if self._mode == "transform":
            self._gen_btn.configure(
                text="Generate", state="normal", fg_color=ACCENT)
        else:
            self._up_btn_go.configure(
                text="Upscale", state="normal", fg_color=ACCENT)
        for p in paths:
            self._gallery.append_image(p)
        threading.Thread(
            target=add_to_history, args=(paths, page), daemon=True).start()

    def _on_error(self, msg: str, mode: str):
        self._overlay.configure(text="")
        if mode == "transform":
            self._gen_btn.configure(
                text="Generate", state="normal", fg_color=ACCENT)
        else:
            self._up_btn_go.configure(
                text="Upscale", state="normal", fg_color=ACCENT)
        if self._toast:
            self._toast(msg, "error")

    def _load_history(self):
        def _run():
            try:
                history = load_history()
                paths = [h["path"] for h in history
                         if h.get("page") in ("img2img", "upscale")]
                self.after(0, lambda: self._gallery.set_images(paths))
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()
