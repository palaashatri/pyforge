# macOS — Build & Run Instructions

PyForge Studio is a pure-Python app. There is no Xcode project or CMake to run.

---

## Option A — Development (recommended for first run)

### Prerequisites

- **Python 3.10 – 3.12** — use Homebrew (`brew install python@3.12`) or [python.org](https://python.org)
- **Xcode Command Line Tools** — only for Homebrew: `xcode-select --install`
- Apple Silicon (M1/M2/M3): MPS acceleration is used automatically
- Intel Mac: CPU-only by default (CUDA not available on macOS)

### Step 1 — Run the setup script

```bash
bash setup.sh
```

This creates `.venv/`, installs all dependencies, and writes two launcher files:
- `run_pyforge.sh` — terminal launcher
- `PyForgeStudio.command` — double-clickable in Finder

### Step 2 — Allow the .command to open (first time only)

macOS may block the `.command` file on first launch:

1. Right-click `PyForgeStudio.command` → **Open**
2. Click **Open** in the security dialog

After that, double-clicking works normally.

### Step 3 — Launch

```bash
bash run_pyforge.sh
# — or —
./.venv/bin/python run.py
```

---

## Option B — Standalone `.app` with PyInstaller

Produces `dist/PyForgeStudio.app` which you can drag to `/Applications` or distribute as a DMG.

> ⚠️ **Size warning:** Bundling torch + diffusers produces a ~10 GB `.app`.
> For a lightweight build that omits AI deps, see the SLIM BUILD comments
> in `packaging/macos/pyforge.spec`.

### Prerequisites (in addition to Option A)

```bash
.venv/bin/pip install pyinstaller
```

### Build the .app

```bash
.venv/bin/pyinstaller packaging/macos/pyforge.spec
```

Output: `dist/PyForgeStudio.app`

### Create a DMG for distribution

```bash
# Install create-dmg for a polished DMG (optional but recommended)
brew install create-dmg

bash packaging/macos/make_dmg.sh
```

Output: `dist/PyForgeStudio.dmg`

### Code-sign & notarise (Apple Developer account required)

```bash
# Sign
codesign --deep --sign "Developer ID Application: Your Name (TEAMID)" \
    --options runtime \
    dist/PyForgeStudio.app

# Create notarisation submission
xcrun notarytool submit dist/PyForgeStudio.dmg \
    --apple-id you@example.com \
    --team-id TEAMID \
    --password APP_SPECIFIC_PW \
    --wait

# Staple the ticket
xcrun stapler staple dist/PyForgeStudio.dmg
```

---

## Apple Silicon (M-series) notes

- torch is installed without an index URL — it picks up the native `arm64` wheel automatically.
- MPS acceleration (`torch.backends.mps.is_available()`) is detected at runtime via `config.device = "auto"`.
- If generation hangs, set `Settings → Device → cpu` as a fallback.
- xFormers is **not** available on Apple Silicon; leave the xFormers toggle off.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python3` not found | `brew install python@3.12` |
| `tkinter` not available | `brew install python-tk@3.12` (Homebrew Python ships without Tk by default) |
| App won't open ("unidentified developer") | Right-click → Open → Open |
| MPS out of memory | `Settings → Device → cpu` |
| `customtkinter` assets missing in .app | Rebuild — `collect_all("customtkinter")` in the spec handles this |
