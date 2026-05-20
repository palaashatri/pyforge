# Windows — Build & Run Instructions

PyForge Studio is a pure-Python app. There is no C++ or Qt to compile.
Setup takes ~5 minutes (mostly downloading PyTorch).

---

## Option A — Development (recommended for first run)

### Prerequisites

- **Python 3.10 – 3.12** from [python.org](https://python.org)
  - ✅ Check "Add Python to PATH" during install
- **Git** (optional, only needed to clone)
- **NVIDIA GPU + CUDA** recommended; CPU-only works but generation is slow

### Step 1 — Run the setup script

Open PowerShell in the project root and run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1
```

This creates `.venv\`, installs all dependencies, and writes `PyForgeStudio.bat`.

> **PyTorch variant** — by default `setup.ps1` installs CUDA 12.1 torch.
> Edit the `$TORCH_INDEX_URL` line near the top to change it:
>
> | Variant | URL |
> |---|---|
> | CUDA 12.4 | `https://download.pytorch.org/whl/cu124` |
> | CUDA 11.8 | `https://download.pytorch.org/whl/cu118` |
> | CPU only  | `https://download.pytorch.org/whl/cpu`   |

### Step 2 — Launch

Double-click **`PyForgeStudio.bat`** — or from PowerShell:

```powershell
.\.venv\Scripts\python.exe run.py
```

---

## Option B — Standalone `.exe` with PyInstaller

Produces a self-contained `dist\PyForgeStudio\` folder you can zip and share.

> ⚠️ **Size warning:** Bundling torch + diffusers produces ~10 GB output.
> For a lightweight build that omits AI deps, see the SLIM BUILD comments
> in `packaging/windows/pyforge.spec`.

### Prerequisites (in addition to Option A)

```powershell
.venv\Scripts\pip install pyinstaller
```

### Build

```powershell
.\.venv\Scripts\pyinstaller packaging\windows\pyforge.spec
```

Output: `dist\PyForgeStudio\PyForgeStudio.exe`

### (Optional) Create an installer with Inno Setup

Install [Inno Setup](https://jrsoftware.org/isinfo.php), then create a script like:

```iss
[Setup]
AppName=PyForge Studio
AppVersion=1.0.0
DefaultDirName={autopf}\PyForge Studio
OutputBaseFilename=PyForgeStudio-Setup
Compression=lzma2/ultra64

[Files]
Source: "dist\PyForgeStudio\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{autoprograms}\PyForge Studio"; Filename: "{app}\PyForgeStudio.exe"
Name: "{autodesktop}\PyForge Studio";  Filename: "{app}\PyForgeStudio.exe"

[Run]
Filename: "{app}\PyForgeStudio.exe"; Description: "Launch PyForge Studio"; Flags: nowait postinstall
```

Compile with `iscc pyforge_setup.iss` to produce a single `.exe` installer.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` not found | Re-install Python and check "Add to PATH" |
| CUDA not available in torch | Ensure NVIDIA drivers ≥ 527; re-run `setup.ps1` and pick the right CUDA URL |
| `customtkinter` import error | Run `.venv\Scripts\pip install --upgrade customtkinter` |
| Generation crashes immediately | Try `Settings → Device → cpu` to rule out GPU issues |
| Download stuck at 0% | Check your HuggingFace token and internet connection |
