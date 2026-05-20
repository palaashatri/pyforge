# PyInstaller spec — PyForge Studio (Linux)
#
# Build from the project root:
#   .venv/bin/pyinstaller packaging/linux/pyforge.spec
#
# Output: dist/PyForgeStudio/PyForgeStudio   (one-directory build)
#
# Wrap in an AppImage or .deb using the steps in build_instructions.md.
#
# NOTE: Including torch + diffusers produces a ~10 GB dist folder.
# See SLIM BUILD section below.

from pathlib import Path
from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).parent.parent  # repo root

ctk_data,   ctk_bins,   ctk_imports   = collect_all("customtkinter")
PIL_data,   PIL_bins,   PIL_imports   = collect_all("PIL")
diff_data,  diff_bins,  diff_imports  = collect_all("diffusers")
trans_data, trans_bins, trans_imports = collect_all("transformers")
hfhub_data, hfhub_bins, hfhub_imports = collect_all("huggingface_hub")

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
# To produce a lightweight binary that only bundles the UI layer, replace
# the sections above with:
#   all_imports = ctk_imports + PIL_imports + ["tkinter", "tkinter.filedialog"]
#   all_datas   = ctk_data + PIL_data
#   all_binaries = ctk_bins + PIL_bins
# Then distribute alongside setup.sh so users install torch/diffusers separately.
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
    strip=True,
    upx=True,
    console=False,
    icon=str(ROOT / "packaging" / "linux" / "icon.png") if (ROOT / "packaging" / "linux" / "icon.png").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name="PyForgeStudio",
)
