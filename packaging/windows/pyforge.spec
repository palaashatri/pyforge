# PyInstaller spec — PyForge Studio (Windows)
#
# Build from the project root:
#   .venv\Scripts\pyinstaller packaging\windows\pyforge.spec
#
# Output: dist\PyForgeStudio\PyForgeStudio.exe   (one-directory build)
#
# NOTE: Including torch + diffusers produces a ~10 GB dist folder.
# See SLIM BUILD section below to exclude AI deps and keep the output small.

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

ROOT = Path(SPECPATH).parent.parent  # repo root

# ── Collect assets for packages that hide data files from PyInstaller ─────────
ctk_data,    ctk_bins,    ctk_imports    = collect_all("customtkinter")
PIL_data,    PIL_bins,    PIL_imports    = collect_all("PIL")
diff_data,   diff_bins,   diff_imports   = collect_all("diffusers")
trans_data,  trans_bins,  trans_imports  = collect_all("transformers")
hfhub_data,  hfhub_bins,  hfhub_imports  = collect_all("huggingface_hub")

all_datas    = ctk_data + PIL_data + diff_data + trans_data + hfhub_data
all_binaries = ctk_bins + PIL_bins + diff_bins + trans_bins + hfhub_bins
all_imports  = (ctk_imports + PIL_imports + diff_imports +
                trans_imports + hfhub_imports +
                [
                    "tkinter", "tkinter.filedialog",
                    "torch", "torchvision",
                    "accelerate", "safetensors",
                ])

# ── SLIM BUILD ─────────────────────────────────────────────────────────────────
# To build a smaller package that requires torch/diffusers to be installed
# separately in a venv, comment out the torch/diffusers lines above and set:
#   all_imports = ctk_imports + PIL_imports + ["tkinter", "tkinter.filedialog"]
#   all_datas   = ctk_data + PIL_data
# Then distribute alongside a setup.ps1 that installs AI deps.
# The .exe will still launch and show the UI; generation will fail unless the
# user also installs torch+diffusers into the same environment.
# ─────────────────────────────────────────────────────────────────────────────

a = Analysis(
    [str(ROOT / "run.py")],
    pathex=[str(ROOT)],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "notebook", "IPython", "pytest", "sphinx"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PyForgeStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,         # no console window
    icon=str(ROOT / "packaging" / "windows" / "icon.ico") if (ROOT / "packaging" / "windows" / "icon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PyForgeStudio",
)
