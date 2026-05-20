# Linux — Build & Run Instructions

PyForge Studio is a pure-Python app. No compilation required.

---

## Option A — Development (recommended for first run)

### Prerequisites

**Ubuntu / Debian:**
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3-tk git
```

**Fedora / RHEL:**
```bash
sudo dnf install python3.12 python3-tkinter git
```

**Arch:**
```bash
sudo pacman -S python tk git
```

> **tkinter** must be the system-installed version — it cannot be pip-installed.
> On Ubuntu `python3-tk` provides it; on Fedora it's `python3-tkinter`.

### Step 1 — Run the setup script

```bash
bash setup.sh
```

This creates `.venv/`, installs all dependencies, and writes `run_pyforge.sh`.

> **PyTorch variant** — `setup.sh` defaults to CUDA 12.1 on Linux.
> Edit the `pip install torch` line to change it:
>
> ```bash
> # CPU only
> .venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
>
> # CUDA 11.8
> .venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
> ```

### Step 2 — Launch

```bash
bash run_pyforge.sh
# — or —
./.venv/bin/python run.py
```

---

## Option B — AppImage with PyInstaller

Produces a portable `dist/PyForgeStudio` directory that runs on any glibc-compatible Linux.

> ⚠️ **Size warning:** Bundling torch + diffusers produces ~10 GB output.
> For a lightweight build, see the SLIM BUILD comments in the spec below.

### Prerequisites (in addition to Option A)

```bash
.venv/bin/pip install pyinstaller
```

### Build

```bash
.venv/bin/pyinstaller packaging/linux/pyforge.spec
```

Output: `dist/PyForgeStudio/PyForgeStudio`

### Wrap in an AppImage (optional)

```bash
# Install linuxdeploy
wget -q https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
chmod +x linuxdeploy-x86_64.AppImage

# Create AppDir structure
mkdir -p AppDir/usr/bin AppDir/usr/share/applications AppDir/usr/share/icons/hicolor/256x256/apps

cp -r dist/PyForgeStudio/* AppDir/usr/bin/

cat > AppDir/usr/share/applications/pyforge-studio.desktop <<'EOF'
[Desktop Entry]
Name=PyForge Studio
Exec=PyForgeStudio
Icon=pyforge-studio
Type=Application
Categories=Graphics;
EOF

# Copy icon if available
# cp packaging/linux/icon.png AppDir/usr/share/icons/hicolor/256x256/apps/pyforge-studio.png

./linuxdeploy-x86_64.AppImage --appdir AppDir --output appimage
```

Output: `PyForge_Studio-x86_64.AppImage`

### Option C — .deb package

```bash
VERSION="1.0.0"
PKG="pyforge-studio_${VERSION}_amd64"

mkdir -p "$PKG/usr/lib/pyforge-studio"
mkdir -p "$PKG/usr/bin"
mkdir -p "$PKG/DEBIAN"

cp -r dist/PyForgeStudio/* "$PKG/usr/lib/pyforge-studio/"

# Wrapper script so it appears on PATH
cat > "$PKG/usr/bin/pyforge-studio" <<'EOF'
#!/bin/bash
exec /usr/lib/pyforge-studio/PyForgeStudio "$@"
EOF
chmod +x "$PKG/usr/bin/pyforge-studio"

cat > "$PKG/DEBIAN/control" <<EOF
Package: pyforge-studio
Version: $VERSION
Architecture: amd64
Maintainer: PyForge <you@example.com>
Description: PyForge Studio — local AI image generator
 Stable Diffusion text-to-image, img2img, inpainting, upscaling, and ControlNet.
 All processing is local. No internet required after model download.
EOF

dpkg-deb --build "$PKG" "${PKG}.deb"
echo "Package: ${PKG}.deb"
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: tkinter` | `sudo apt install python3-tk` (Ubuntu) or `sudo dnf install python3-tkinter` (Fedora) |
| CUDA not found | Verify `nvidia-smi` works; re-run setup with correct CUDA URL |
| Screen scaling looks wrong | `export GDK_SCALE=1` before launching; or pass `--scale 1.0` |
| `libGL.so.1` missing (headless) | `sudo apt install libgl1` |
| App crashes on Wayland | `export GDK_BACKEND=x11` before launching (CTk uses Xlib) |
