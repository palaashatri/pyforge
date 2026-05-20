# PyInstaller spec — PyForge Studio (macOS)
#
# Build from the project root:
#   .venv/bin/pyinstaller packaging/macos/pyforge.spec
#
# Output: dist/PyForgeStudio.app
#
# After building, create a DMG:
#   bash packaging/macos/make_dmg.sh
#
# NOTE: Including torch + diffusers produces a ~10 GB .app bundle.
# See SLIM BUILD section below to exclude AI deps.

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
# To produce a lightweight .app that only bundles the UI + core code,
# comment out the torch/diffusers sections above and keep only:
#   all_imports = ctk_imports + PIL_imports + ["tkinter", "tkinter.filedialog"]
#   all_datas   = ctk_data + PIL_data
# Distribute alongside setup.sh so users install AI deps into the same venv.
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
    upx=False,         # UPX not recommended on macOS
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="PyForgeStudio",
)

app = BUNDLE(
    coll,
    name="PyForgeStudio.app",
    icon=str(ROOT / "packaging" / "macos" / "icon.icns") if (ROOT / "packaging" / "macos" / "icon.icns").exists() else None,
    bundle_identifier="com.pyforge.studio",
    info_plist={
        "NSPrincipalClass":                  "NSApplication",
        "NSHighResolutionCapable":           True,
        "CFBundleShortVersionString":        "1.0.0",
        "CFBundleVersion":                   "1.0.0",
        "NSHumanReadableCopyright":          "PyForge Studio",
        "NSRequiresAquaSystemAppearance":    False,   # allow dark mode
        "LSMinimumSystemVersion":            "12.0",
    },
)
