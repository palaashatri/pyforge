# PyForge Studio

A cross-platform desktop app for local AI image generation — DiffusionBee-style UI built with Qt 6/QML + Python Diffusers backend.

## Features

- **Text to Image** — SD 1.5 / SDXL / Flux
- **Image to Image** — strength-controlled variations
- **Inpainting** — canvas mask drawing + in-fill
- **Upscaler** — 2× / 4× via Real-ESRGAN or latent upscaler
- **ControlNet** — Canny, Depth, Pose, Scribble, and more
- **Model Manager** — download any HuggingFace diffusion model
- **100% local** — no cloud, no telemetry

## Quick start (development)

### 1. Python backend

```bash
python -m venv backend/.venv
# Windows:
backend\.venv\Scripts\pip install -e backend
# macOS/Linux:
backend/.venv/bin/pip install -e backend

# Run the server:
backend/.venv/Scripts/python backend/src/server.py --port 8765
```

### 2. Qt frontend

```bash
cmake -B build -DCMAKE_PREFIX_PATH=/path/to/Qt/6.x/platform
cmake --build build --parallel
./build/frontend/PyForgeStation   # or build\frontend\Release\PyForgeStation.exe
```

### 3. Download a model

Open the **Models** tab → paste a HuggingFace repo ID (e.g. `runwayml/stable-diffusion-v1-5`) → click **Download**.

## Project structure

```
pyforge-station/
  frontend/          Qt 6 / QML application
  backend/           Python FastAPI + Diffusers server
  packaging/         Build & distribution instructions
  CLAUDE.md          Milestone tracker & architecture spec
```

## Build & packaging

See:
- [`packaging/windows/build_instructions.md`](packaging/windows/build_instructions.md)
- [`packaging/macos/build_instructions.md`](packaging/macos/build_instructions.md)
- [`packaging/linux/build_instructions.md`](packaging/linux/build_instructions.md)
