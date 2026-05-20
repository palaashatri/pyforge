# PyForge Studio

A cross-platform desktop app for local AI image generation — built entirely in Python with a customtkinter UI and Diffusers backend. No cloud, no telemetry, no separate server process.

## Features

- **Text to Image** — SD 1.5 / SDXL / Flux, full prompt + CFG + seed + batch controls
- **Image to Image** — strength-controlled variations with live input preview
- **Upscaler** — continuous 1×–8× scale via Real-ESRGAN or latent fallback, integrated into the Image to Image page
- **Inpainting** — brush mask drawn on canvas, prompt-guided fill
- **ControlNet** — 6 conditioning types (Canny, Depth, Pose, …) with conditioning scale
- **Model Manager** — browse top HuggingFace text-to-image models sorted by downloads, one-click download with live progress bar, per-download cancel, and parallel downloads. Model sizes shown in the catalog.
- **Settings** — device (CUDA / MPS / CPU), xFormers, image format, output directory, dark/light/system theme
- **Developer font picker** — drop any `.ttf`/`.otf` into `.fonts/`, pick from a dropdown in Settings, restart to apply
- **100% local** — all processing runs on your machine after the initial model download

## Quick start

### Windows

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1
```

Then double-click **`PyForgeStudio.bat`** — or from PowerShell:

```powershell
.\.venv\Scripts\python.exe run.py
```

### macOS

```bash
bash setup.sh
bash run_pyforge.sh
```

### Linux

```bash
bash setup_linux.sh
bash run_pyforge.sh
```

`setup_linux.sh` handles system tkinter detection (`python3-tk`), Python 3.10+ discovery, ARM64 vs x86_64 PyTorch selection (CPU / CUDA 12.4), and writes a `run_pyforge.sh` launcher.

### Manual install (any platform)

```bash
pip install customtkinter Pillow

# Pick your PyTorch variant:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124   # CUDA 12.4
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu     # CPU only

pip install diffusers transformers huggingface_hub accelerate
python run.py
```

## Project structure

```
pyforge-station/
  run.py                   entry point (DPI awareness + custom font pre-load)
  setup.ps1                Windows setup script
  setup.sh                 macOS/Linux setup script
  setup_linux.sh           Linux-specific setup (tkinter check, ARM64 torch)
  PyForgeStudio.bat        Windows launcher
  .fonts/                  drop custom .ttf/.otf files here for the font picker
  app/
    main.py
    core/                  AI / data logic (no UI imports)
      config.py            settings  (~/.pyforge/config.json)
      fonts.py             local font scanner, TTF name reader, OS font loader
      manager.py           HuggingFace model download, registry, browse, sizes
      pipelines.py         diffusers pipelines (lazy-loaded, cached)
      paths.py             output filename generation
      history.py           generation history (~/.pyforge/history.json)
    ui/
      app_window.py        CTk root window, sidebar, page switching
      sidebar.py           navigation sidebar
      topbar.py            title + status pill
      theme.py             (light, dark) colour tuples, blend_hex, OS-aware font
      components/
        toast.py           slide-in notifications
        image_gallery.py   scrollable thumbnail grid + detail view
        prompt_panel.py    shared generation controls
      pages/
        txt2img_page.py
        img2img_page.py    includes Upscale mode
        inpaint_page.py
        upscale_page.py
        controlnet_page.py
        models_page.py     Discover / Installed / Diagnostics tabs
        settings_page.py
  packaging/
    windows/
    macos/
    linux/
```

## Custom fonts (Developer Option)

1. Create a `.fonts/` folder next to `run.py`.
2. Drop any `.ttf` or `.otf` file into it (e.g. download **Inter** from [fonts.google.com](https://fonts.google.com/specimen/Inter) → *Download family*).
3. Open **Settings** → click **Developer Options (show)** at the bottom.
4. Click **Scan** — the dropdown lists every font found.
5. Select one, click **Apply Font**, then restart PyForge.

The font family name is read directly from the file's name table (no filename guessing). On Windows the font is loaded privately via `AddFontResourceExW` (no admin rights, no system pollution). On macOS it's copied to `~/Library/Fonts`; on Linux to `~/.local/share/fonts` with `fc-cache`.

## Packaging

See the platform-specific build instructions:

- [`packaging/windows/build_instructions.md`](packaging/windows/build_instructions.md) — PyInstaller `.exe` + optional Inno Setup installer
- [`packaging/macos/build_instructions.md`](packaging/macos/build_instructions.md) — PyInstaller `.app` + DMG
- [`packaging/linux/build_instructions.md`](packaging/linux/build_instructions.md) — PyInstaller + AppImage or `.deb`

## Data locations

| Data | Path |
|---|---|
| Models | Windows: `%LOCALAPPDATA%\PyForge\models` · macOS: `~/Library/Application Support/PyForge/models` · Linux: `~/.local/share/pyforge/models` |
| Outputs | `~/.pyforge/outputs/` |
| Config | `~/.pyforge/config.json` |
| History | `~/.pyforge/history.json` |
| Custom fonts | `<repo>/.fonts/`  or  `~/.pyforge/fonts/` |

## Requirements

- **Python 3.10 – 3.14**
- `customtkinter >= 5.2.0`, `Pillow >= 10.0.0`
- `torch`, `diffusers`, `transformers`, `huggingface_hub >= 1.0`, `accelerate`
- Optional: `xformers` (VRAM reduction), `realesrgan` + `basicsr` (Real-ESRGAN upscaling)
