# PyForge Studio

A cross-platform desktop app for local AI image generation — built entirely in Python with a customtkinter UI and Diffusers backend. No cloud, no telemetry, no separate server process.

## Features

- **Text to Image** — SD 1.5 / SDXL / Flux, full prompt + CFG + seed + batch controls
- **Image to Image** — strength-controlled variations with live input preview
- **Upscaler** — continuous 1×–8× scale via Real-ESRGAN or latent fallback, integrated into the Image to Image page
- **Model Manager** — browse the top HuggingFace text-to-image models sorted by downloads, one-click download with live progress
- **Settings** — device (CUDA / MPS / CPU), xFormers, image format, output directory, dark/light/system theme
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

### macOS / Linux

```bash
bash setup.sh
bash run_pyforge.sh
```

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
  run.py                   entry point
  setup.ps1                Windows setup script
  setup.sh                 macOS / Linux setup script
  PyForgeStudio.bat        Windows launcher
  app/
    main.py
    core/                  AI / data logic (no UI imports)
      config.py            settings  (~/.pyforge/config.json)
      manager.py           HuggingFace model download, registry, browse
      pipelines.py         diffusers pipelines (lazy-loaded, cached)
      paths.py             output filename generation
      history.py           generation history (~/.pyforge/history.json)
    ui/
      app_window.py        CTk root window, sidebar, page switching
      sidebar.py           navigation sidebar
      topbar.py            title + status pill
      theme.py             colour palette, fonts, blend_hex helper
      components/
        toast.py           slide-in notifications
        image_gallery.py   scrollable thumbnail grid + detail view
        prompt_panel.py    shared generation controls (txt2img)
      pages/
        txt2img_page.py
        img2img_page.py    includes Upscale mode
        models_page.py     Discover / Installed / Diagnostics tabs
        settings_page.py
  packaging/
    windows/
    macos/
    linux/
```

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

## Requirements

- **Python 3.10 – 3.14**
- `customtkinter >= 5.2.0`, `Pillow >= 10.0.0`
- `torch`, `diffusers`, `transformers`, `huggingface_hub >= 1.0`, `accelerate`
- Optional: `xformers` (VRAM reduction), `realesrgan` + `basicsr` (Real-ESRGAN upscaling)
