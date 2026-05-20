#!/usr/bin/env bash
# Creates a distributable DMG from the PyInstaller .app bundle.
# Run from the project root after:  .venv/bin/pyinstaller packaging/macos/pyforge.spec

set -euo pipefail

APP="dist/PyForgeStudio.app"
DMG="dist/PyForgeStudio.dmg"

if [[ ! -d "$APP" ]]; then
    echo "ERROR: $APP not found. Run PyInstaller first:" >&2
    echo "  .venv/bin/pyinstaller packaging/macos/pyforge.spec" >&2
    exit 1
fi

# Check for create-dmg (brew install create-dmg)
if command -v create-dmg &>/dev/null; then
    create-dmg \
        --volname "PyForge Studio" \
        --volicon "packaging/macos/icon.icns" \
        --window-size 660 400 \
        --icon-size 128 \
        --icon "PyForgeStudio.app" 160 185 \
        --hide-extension "PyForgeStudio.app" \
        --app-drop-link 500 185 \
        "$DMG" \
        "dist/"
    echo "DMG created: $DMG"
else
    # Fallback: plain hdiutil DMG (no background or layout)
    echo "create-dmg not found — using plain hdiutil DMG."
    echo "Install for a prettier result: brew install create-dmg"
    hdiutil create -volname "PyForge Studio" \
        -srcfolder "dist/PyForgeStudio.app" \
        -ov -format UDZO "$DMG"
    echo "DMG created: $DMG"
fi
