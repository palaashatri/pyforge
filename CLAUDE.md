# CLAUDE.md — PyForge Studio

> **Stack:** Python 3 · customtkinter (CTk) · diffusers · huggingface_hub  
> **Goal:** A polished, cross-platform desktop app for local AI image generation — text-to-image, img2img, inpainting, upscaling, ControlNet — with a built-in HuggingFace model manager.  
> All logic runs in a single Python process. No separate server, no HTTP, no subprocesses.

---

## 0. Status & milestones

### 0.1 High-level milestones

- [x] **M1: Project scaffolding**
  > `app/` package structure, `run.py` launcher, `core/` for AI logic, `ui/` for the interface.

- [x] **M2: Core UI shell & navigation**
  > `AppWindow` (CTk), `Sidebar` (nav items, accent-tint selection), `TopBar` (title + status pill), `Toast` notification component, page-switching via grid show/hide.

- [x] **M3: Model manager & HuggingFace downloader**
  > `core/manager.py` — `list_models`, `download_model`, `delete_model`, `get_model_path`. Registry stored in `~/.pyforge/models/registry.json`. Download progress polled via shared dict at 300 ms intervals. `ModelsPage` shows installed models with delete, download form with live progress bar, cancel button, and parallel downloads. Catalog shows async-fetched model sizes via `fetch_model_size()`.

- [x] **M4: Text-to-image pipeline wired to UI**
  > `core/pipelines.py` — lazy-loaded SD 1.5 / SDXL auto-detect, seed, batch. `TextToImagePage` with `PromptPanel` + `ImageGallery`. History persisted to `~/.pyforge/history.json`.

- [x] **M5: Advanced image tools**
  > img2img (strength slider), inpainting (tk.Canvas mask → base64 PNG), upscaler (Real-ESRGAN / latent fallback), ControlNet (6 types, conditioning scale). All wired directly to `core/pipelines.py`.

- [x] **M6: Settings & config persistence**
  > `core/config.py` — reads/writes `~/.pyforge/config.json`. Settings page saves device, xFormers, image format, output dir, theme, custom font. Instant save — no HTTP round-trip.

- [x] **M7: Dead code removal & architecture simplification**
  > Removed Qt/QML/C++ frontend (`frontend/`), FastAPI server (`backend/`), CMake build system, `BackendManager`, all HTTP calls. Single-process Python app. ~200 lines of infrastructure deleted.

- [x] **M8a: UI polish**
  > Windows DPI awareness (`SetProcessDpiAwareness`), Windows 11 font detection (`Segoe UI Variable`), full light/dark theme support via CTk colour tuples, developer font picker (drop `.ttf`/`.otf` into `.fonts/`).

- [ ] **M8b: Packaging**
  > `run.py` works for development. One-file `.exe` (PyInstaller), `.app` (py2app), and AppImage not yet done.

---

## 0.2 Current status (June 2026)

The app is fully functional as a Python application. Run with:

```bash
pip install customtkinter Pillow
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install diffusers transformers huggingface_hub accelerate
python run.py
```

### Architecture

```
pyforge-station/
  run.py                  ← entry point (DPI awareness + custom font pre-load)
  setup.ps1               ← Windows one-shot setup
  setup.sh                ← macOS/Linux setup
  setup_linux.sh          ← Linux-specific setup (tkinter check, ARM64 torch)
  app/
    main.py
    core/                 ← all AI / data logic (no UI dependency)
      config.py           — settings R/W  (~/.pyforge/config.json)
      fonts.py            — local font scanner, TTF name-table reader, OS loader
      manager.py          — HF model download, registry, list, delete, browse
      pipelines.py        — diffusers pipelines (lazy-loaded, cached)
      paths.py            — output filename generation
      history.py          — generation history R/W (~/.pyforge/history.json)
    ui/
      app_window.py       — CTk root window, sidebar, topbar, page switching
      sidebar.py          — navigation sidebar
      topbar.py           — title + status pill
      theme.py            — (light, dark) colour tuples, blend_hex, OS-aware font
      components/
        toast.py          — slide-in notification (error / success / info)
        image_gallery.py  — scrollable 3-col thumbnail grid, CTkImage detail view
        prompt_panel.py   — all generation controls (reused by 3 pages)
      pages/
        txt2img_page.py
        img2img_page.py
        inpaint_page.py
        upscale_page.py
        controlnet_page.py
        models_page.py
        settings_page.py
  .fonts/                 ← drop custom .ttf/.otf files here (Developer Options)
  packaging/
    windows/build_instructions.md
    macos/build_instructions.md
    linux/build_instructions.md
```

### Key design decisions

| Decision | Reason |
|---|---|
| Single Python process | UI is Python/CTk — no need for a separate server or HTTP |
| Lazy pipeline loading | Window opens instantly; torch/diffusers load on first generation |
| `threading.Thread` + `.after()` | All blocking work off the main thread; results posted back safely |
| Progress dict polling | `download_model()` writes to a shared dict; UI polls at 300 ms — simpler than SSE |
| `~/.pyforge/` data dir | Cross-platform, user-owned, no admin rights needed |
| CTk `(light, dark)` colour tuples | All theme constants are tuples; `set_appearance_mode()` switches automatically |
| Local font loading | `fonts.py` reads TTF name tables with `struct`; `AddFontResourceExW` / `~/Library/Fonts` / `fc-cache` with no admin rights |

### What was removed vs the original spec

The original spec called for Qt 6 / QML / C++ frontend + FastAPI Python backend (two processes, HTTP). This was scrapped after the Qt frontend was built, in favour of an all-Python CTk app:

- ~~`frontend/`~~ — Qt/QML/C++ (deleted)
- ~~`backend/src/server.py`~~ — FastAPI app (deleted)
- ~~`CMakeLists.txt`~~ — CMake build (deleted)
- ~~`BackendManager`~~ — subprocess spawner (deleted)
- ~~`requests`~~ — HTTP client (deleted; was in every page)

---

## 1. Tech stack

| Layer | Technology |
|---|---|
| UI framework | `customtkinter` (CTk) — dark-themed tkinter wrapper |
| AI pipelines | `diffusers`, `transformers`, `torch` |
| Model downloads | `huggingface_hub.snapshot_download` / `hf_hub_download` |
| Image I/O | `Pillow` |
| Upscaling (optional) | `realesrgan`, `basicsr` |

**Python >= 3.10** required (uses `match`, `|` union types).

---

## 2. Running & installing

### Development

```bash
# 1. Clone
git clone ...
cd pyforge-station

# 2. Install UI deps
pip install customtkinter Pillow

# 3. Install AI deps (pick your CUDA version)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install diffusers transformers huggingface_hub accelerate

# 4. Optional: upscaling support
pip install xformers realesrgan basicsr

# 5. Run
python run.py
```

### Packaging (M8b — not yet done)

See `packaging/` for build instructions once PyInstaller / py2app packaging is added.

---

## 3. Pages & features

| Page | Key controls | Core function called |
|---|---|---|
| Text to Image | Prompt, negative, model, resolution, steps, CFG, seed, batch | `generate_txt2img()` |
| Image to Image | Input image picker, strength slider + all prompt controls | `generate_img2img()` |
| Inpainting | tk.Canvas brush mask, prompt, model | `generate_inpaint()` |
| Upscaler | Image picker, 2×/4×, model | `generate_upscale()` |
| Control Images | Control image, CN type, conditioning scale + prompt controls | `generate_controlnet()` |
| Models | HF catalog with async sizes, one-click download with progress + cancel, parallel downloads, installed list | `download_model()` / `list_models()` / `delete_model()` / `fetch_model_size()` |
| Settings | Device, xFormers, image format, output dir, theme, developer font picker | `config.update()` |

---

## 4. Data locations

| Data | Path |
|---|---|
| Models | Windows: `%LOCALAPPDATA%\PyForge\models`  macOS: `~/Library/Application Support/PyForge/models`  Linux: `~/.local/share/pyforge/models` |
| Outputs | `~/.pyforge/outputs/` |
| Config | `~/.pyforge/config.json` |
| History | `~/.pyforge/history.json` |
| Custom fonts | `<project_root>/.fonts/`  or  `~/.pyforge/fonts/` |

---

## 5. Remaining work (M8b)

- [ ] PyInstaller spec for Windows `.exe` (bundle CTk, Pillow, torch, diffusers)
- [ ] py2app spec for macOS `.app`
- [ ] AppImage / `.deb` for Linux
- [ ] Drag-and-drop onto image pickers (img2img, inpainting, upscaler, ControlNet)
- [ ] Cancel button for in-progress generation (needs `stop_event` threaded into `core/pipelines.py`)

---

## 6. Claude instructions

When working on this codebase:

1. **Never reintroduce HTTP or subprocess** — all backend calls go through `app/core/` directly.
2. **Keep `core/` free of UI imports** — `app/core/*.py` must not import from `app/ui/`.
3. **All blocking work in threads** — any call to `core/` goes in `threading.Thread(daemon=True)`, result posted back via `widget.after(0, callback)`.
4. **Colours are always `(light, dark)` tuples** — never hardcode a single hex string for a UI colour constant. ACCENT/ACCENT_HOVER/ACCENT_DARK are the only string exceptions (same shade on both themes).
5. **Update this file** when milestones are completed or the architecture changes.
