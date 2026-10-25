# AGENTS.md — PyForge Studio

PyForge Studio is a single-process Python desktop app for local image generation: a customtkinter (CTk) UI over Hugging Face `diffusers`, with a built-in Hugging Face model browser/downloader. No server, no HTTP between UI and backend, no subprocesses.

(This file replaces the old `CLAUDE.md`; Claude Code, Codex and Cursor all read `AGENTS.md`.)

## Current state (2026-10-20)

What the UI actually exposes:

| Page | Backend call | State |
|---|---|---|
| Text to Image | `generate_txt2img()` | Works for SD 1.5 and SDXL checkpoints |
| Image to Image (+ upscale) | `generate_img2img()`, `generate_upscale()` | Works; upscale uses Real-ESRGAN if installed, else latent fallback |
| Models | `list_models()`, `download_model()`, `delete_model()`, `fetch_model_size()` | Works |
| Settings | `config.update()` | Works |

Not reachable from the UI, despite README claims: **inpainting** (`generate_inpaint()` exists in `app/core/pipelines.py`, no page) and **ControlNet** (`generate_controlnet()` exists, no page). **Flux** models are detected by name in `manager.py`, but `_load_txt2img` only tries the SDXL and SD 1.5 pipelines, so Flux generation fails.

There are no automated tests and no CI. PyInstaller specs exist in `packaging/{windows,macos,linux}/pyforge.spec` but no packaged build has been verified.

## Commands

Python 3.10+.

```bash
bash setup.sh            # macOS/Linux: creates .venv, installs deps, writes run_pyforge.sh
bash setup_linux.sh      # Linux: also checks python3-tk and picks CPU/CUDA/ARM64 torch
.\setup.ps1              # Windows (then PyForgeStudio.bat)
bash run_pyforge.sh      # or: .venv/bin/python run.py

# manual
pip install -r app/requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121   # pick your CUDA/CPU build
pip install diffusers transformers huggingface_hub accelerate                       # optional: xformers realesrgan basicsr
python run.py

python -m compileall -q app run.py      # cheapest smoke check until tests exist
```

## Layout

```text
run.py                    entry point (DPI awareness, custom font preload)
app/main.py
app/core/                 all AI/data logic — must not import from app/ui
  pipelines.py            lazy-loaded, cached diffusers pipelines (txt2img, img2img, inpaint, upscale, controlnet)
  manager.py              HF catalogue/download/registry, list/delete, size lookup
  config.py, paths.py, history.py, fonts.py
app/ui/                   CTk window, sidebar, topbar, theme, components/, pages/
packaging/                PyInstaller specs and per-OS notes
```

Data: models in `%LOCALAPPDATA%\PyForge\models` / `~/Library/Application Support/PyForge/models` / `~/.local/share/pyforge/models`; outputs, `config.json` and `history.json` in `~/.pyforge/`.

## Rules

1. Never reintroduce HTTP servers or subprocess backends; UI calls `app/core` directly.
2. `app/core/*.py` must not import from `app/ui/`.
3. All blocking work (model load, generation, downloads) runs in `threading.Thread(daemon=True)`; results go back to Tk with `widget.after(0, callback)`. Never touch widgets from a worker thread.
4. UI colour constants are `(light, dark)` tuples (only the ACCENT constants are single strings).
5. README and this file list only features a user can reach in the UI today. A backend function without a page is not a feature.
6. Don't commit models, outputs, `.venv/` or `__pycache__/`.

## Suggested next tasks

1. Add Inpainting and ControlNet pages (backends exist), or remove them from the README.
2. Implement Flux via `diffusers.FluxPipeline` with its own loader, or drop the Flux claim.
3. Add a cancel button: thread a `threading.Event` through `pipelines.py` (diffusers step callback).
4. Add `pytest` tests for `core/` (config round-trip, history, model registry, filename generation) and a GitHub Actions job running them plus `ruff check`.
5. Verify the PyInstaller specs on each OS before calling packaging done.

## Git workflow

Never push to `main`; branch, run the app through the pages you touched, and open a PR saying what you tested on which OS/GPU.

## Background

The project started as a Qt/QML/C++ frontend with a FastAPI backend; that was deleted in favour of one Python process (milestone M7). Don't bring it back.

## Future SLOPOS/PARAMA platforms and Raspberry Pi Zero 2 W efficiency

**FUTURE DESIGN TARGET / NOT IMPLEMENTED.** pyforge is an independently authored candidate for the **optional separately installable SLOPOS creative tool, not a Pi-core app**. Preserve Python, customtkinter and Hugging Face Diffusers/PyTorch. No present SLOPOS package, Linux AArch64 Pi validation or PARAMA native port is implied. Maintain existing milestone/tech-stack rules and inspect all imported code, fonts, runtime libraries and models for license/provenance before first-party distribution.

- **SLOPOS/Linux:** Linux/SLOPOS launcher, portal/file-picker and permissioned image-open/save, metadata, GUI focus, cancel/progress, theme/icon roles where customtkinter supports them; keep Python dependency isolation rather than baking PyTorch into default OS images.
- **Edge efficiency on 4× Cortex-A53 and 512 MB shared memory:** Separate lightweight UI/metadata browsing from model loading; strictly cap preview images, history, download buffers and Python worker memory. Perform model size and CPU/RAM/GPU preflight before importing/loading torch/diffusers where architecture permits. Do not imply 512 MB supports diffusion; on Zero 2 W use a truthful capability-disabled UI or an opt-in remote worker **only when explicitly implemented and consented**. No hidden internet dependency or silent upload of prompts/images.
- **Native PARAMA / SURYA:** Future PARAMA native target needs a real Python interpreter, Tk/CustomTkinter, PyTorch/Diffusers/native tensor operations, graphics/fonts/threads/network/files and package management. This is materially harder than a CPU CLI port. No direct Linux wheel reuse or hypothetical PARAMA runtime is proof.
- **Acceptance:** Record zero-model GUI import and memory behavior on real Pi hardware **only if dependencies install**; enforce refusal before OOM for an oversized model and test cancellation, image output and local-only privacy on actual supported desktops.
- **Instrumentation and boundaries:** Each target documents actual distro/ABI/OS, hardware, dependencies, model versions, cold/warm launch, idle CPU, process tree PSS and peak RSS, whole-system `MemAvailable`, UI input p95, output fidelity and negative/OOM/restart tests. Use bounded streaming work, progress/backpressure, cancellation and clean recovery instead of UI-blocking calls; network/disk delay may take longer but should not block control inputs. Real Pi board acceptance differs from cross-compilation/QEMU. Optional model/runtime downloads are not part of SLOPOS's minimal 512 MB image. PARAMA native readiness must be tested separately from Linux compatibility personality research.
