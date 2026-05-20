"""Custom font support: local font scanner + cross-platform OS loader.

Flow
----
1. User drops .ttf / .otf files into one of two directories:
     <project_root>/.fonts/    (next to run.py — easy dev workflow)
     ~/.pyforge/fonts/         (persistent user data directory)
2. Settings > Developer Options > "Scan" populates a drop-down with every
   discovered font, showing the real family name read from the file's name
   table (with filename as fallback).
3. User picks a font and clicks "Apply Font".
4. ``register_font()`` installs the TTF into the OS font system (no admin).
5. The family name is written to config.custom_font.
6. On the next launch, ``run.py`` calls ``load_custom_font()`` BEFORE the CTk
   window is created so GDI / CoreText / fontconfig sees it from the start.
7. ``theme._pick_font()`` reads config.custom_font and returns it; every CTk
   widget uses it automatically via the FONT_FACE constant.

Platform notes
--------------
Windows — AddFontResourceExW with FR_PRIVATE loads the font privately for
          this process without admin rights.
macOS   — TTF is copied to ~/Library/Fonts (user fonts dir, no sudo needed).
Linux   — TTF is copied to ~/.local/share/fonts and fc-cache -f is run.
"""
from __future__ import annotations

import logging
import struct
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Font directories ──────────────────────────────────────────────────────────

# Project-root .fonts/ — works regardless of cwd because fonts.py is always
# at  app/core/fonts.py  so three .parent calls reach the repo root.
_PROJECT_FONTS_DIR = Path(__file__).resolve().parent.parent.parent / ".fonts"

# Persistent user-data fonts directory
_PYFORGE_FONTS_DIR = Path.home() / ".pyforge" / "fonts"


def _ensure_pyforge_fonts_dir() -> Path:
    _PYFORGE_FONTS_DIR.mkdir(parents=True, exist_ok=True)
    return _PYFORGE_FONTS_DIR


# ── Font scanning ─────────────────────────────────────────────────────────────

def scan_font_dirs() -> list[dict]:
    """Scan all known font directories and return discovered fonts.

    Scans (in order):
      1. <project_root>/.fonts/
      2. ~/.pyforge/fonts/

    Returns a list of dicts:
      "name"   — display string shown in the UI  ("Inter  [Inter.ttf]")
      "family" — font family name for CTk        ("Inter")
      "path"   — Path object pointing to the file
    """
    found: list[dict] = []
    seen: set[Path]   = set()

    for d in (_PROJECT_FONTS_DIR, _PYFORGE_FONTS_DIR):
        if not d.exists():
            continue
        for path in sorted(d.iterdir()):
            if path.suffix.lower() not in (".ttf", ".otf"):
                continue
            real = path.resolve()
            if real in seen:
                continue
            seen.add(real)
            family = _read_font_family(path) or _family_from_filename(path)
            found.append({
                "name":   f"{family}  [{path.name}]",
                "family": family,
                "path":   path,
            })

    return found


def font_dir_paths() -> tuple[Path, Path]:
    """Return (project_fonts_dir, pyforge_fonts_dir) for display in the UI."""
    return _PROJECT_FONTS_DIR, _PYFORGE_FONTS_DIR


# ── TTF/OTF name-table reader ─────────────────────────────────────────────────

def _read_font_family(path: Path) -> str:
    """Read the font family name from a TTF/OTF name table (binary parse).

    Checks Name ID 16 (Typographic Family — preferred) then 1 (Font Family).
    Handles both Windows (UTF-16 BE) and Mac Roman platform encodings.
    Returns an empty string on any failure.
    """
    try:
        data = path.read_bytes()

        # ── Locate the 'name' table ───────────────────────────────────────────
        # Offset table layout: tag(4) numTables(2) searchRange(2) ...
        # Table directory starts at byte 12; each record is 16 bytes:
        #   tag(4) checkSum(4) offset(4) length(4)
        num_tables: int = struct.unpack_from(">H", data, 4)[0]
        name_offset: Optional[int] = None

        for i in range(num_tables):
            base = 12 + i * 16
            if data[base: base + 4] == b"name":
                name_offset = struct.unpack_from(">I", data, base + 8)[0]
                break

        if name_offset is None:
            return ""

        # ── Parse name table header ────────────────────────────────────────────
        # format(2)  count(2)  stringOffset(2)
        count       = struct.unpack_from(">H", data, name_offset + 2)[0]
        str_base    = name_offset + struct.unpack_from(">H", data, name_offset + 4)[0]

        # ── Walk NameRecords ───────────────────────────────────────────────────
        # Each record: platformID(2) encodingID(2) languageID(2)
        #              nameID(2)     length(2)     stringOffset(2)
        results: dict[int, str] = {}

        for i in range(count):
            rec         = name_offset + 6 + i * 12
            platform_id = struct.unpack_from(">H", data, rec)[0]
            encoding_id = struct.unpack_from(">H", data, rec + 2)[0]
            name_id     = struct.unpack_from(">H", data, rec + 6)[0]
            length      = struct.unpack_from(">H", data, rec + 8)[0]
            str_off     = struct.unpack_from(">H", data, rec + 10)[0]

            # Only care about family names (1 = Font Family, 16 = Preferred Family)
            if name_id not in (1, 16):
                continue

            raw = data[str_base + str_off: str_base + str_off + length]

            if platform_id == 3 and encoding_id == 1:   # Windows  — UTF-16 BE
                text = raw.decode("utf-16-be", errors="replace").strip("\x00")
            elif platform_id == 1:                       # Macintosh — Mac Roman
                text = raw.decode("mac-roman",  errors="replace")
            else:
                continue

            text = text.strip()
            if text:
                results[name_id] = text  # later entries for the same ID overwrite

        # Name ID 16 (Typographic/Preferred Family) wins over ID 1 (Font Family)
        return results.get(16) or results.get(1) or ""

    except Exception:
        return ""


def _family_from_filename(path: Path) -> str:
    """Derive a readable family name from the filename when the name table fails."""
    stem = path.stem
    for suffix in (
        "-Regular", "_Regular", "-Bold",      "_Bold",
        "-Italic",  "_Italic",  "-Light",     "_Light",
        "-Medium",  "_Medium",  "-SemiBold",  "_SemiBold",
        "-ExtraBold","_ExtraBold","-Thin",    "_Thin",
        "-Black",   "_Black",   "-Condensed", "_Condensed",
        "[wdth,wght]", "[wght]",  # common variable-font suffixes
    ):
        stem = stem.replace(suffix, "")
    words = stem.replace("_", " ").replace("-", " ").replace("[", " ").replace("]", " ").split()
    return " ".join(w.capitalize() for w in words if w)


# ── OS font registration ──────────────────────────────────────────────────────

def register_font(path: Path) -> bool:
    """Register a TTF/OTF file with the OS so tkinter/CTk can use it.

    No admin rights required on any platform.
    Returns True on success, False otherwise (details logged).
    """
    try:
        if sys.platform == "win32":
            return _register_win32(path)
        elif sys.platform == "darwin":
            return _register_macos(path)
        else:
            return _register_linux(path)
    except Exception as exc:
        logger.error("register_font failed for '%s': %s", path, exc)
        return False


def _register_win32(path: Path) -> bool:
    import ctypes
    FR_PRIVATE = 0x10   # load only for this process; no system pollution
    n = ctypes.windll.gdi32.AddFontResourceExW(str(path), FR_PRIVATE, 0)
    if n:
        logger.info("Win32: registered %d face(s) from '%s'", n, path.name)
        return True
    logger.warning("Win32: AddFontResourceExW returned 0 for '%s'", path.name)
    return False


def _register_macos(path: Path) -> bool:
    import shutil
    dest_dir = Path.home() / "Library" / "Fonts"
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest_dir / path.name)
    logger.info("macOS: copied '%s' to ~/Library/Fonts/", path.name)
    return True


def _register_linux(path: Path) -> bool:
    import shutil, subprocess
    dest_dir = Path.home() / ".local" / "share" / "fonts"
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest_dir / path.name)
    try:
        subprocess.run(
            ["fc-cache", "-f", str(dest_dir)],
            timeout=15, capture_output=True, check=False,
        )
        logger.info("Linux: copied '%s' and refreshed fc-cache", path.name)
    except FileNotFoundError:
        logger.warning("Linux: fc-cache not found; font copied but cache not updated")
    except Exception as exc:
        logger.warning("Linux: fc-cache error: %s", exc)
    return True


# ── Startup loader (called from run.py before any CTk window) ─────────────────

def load_custom_font() -> Optional[str]:
    """Register the configured custom font TTF with the OS at startup.

    Must be called BEFORE any CTk/Tk window is created so GDI/Pango sees
    the font when the first widget allocates it.

    Returns the font family name on success, None if nothing is configured
    or the file is missing / registration fails.
    """
    try:
        from .config import config   # lazy import — avoids circular at module level
        family = config.custom_font
        if not family:
            return None

        # Find the TTF in any of the known font directories
        slug = family.replace(" ", "_")
        candidates = [
            _PROJECT_FONTS_DIR,
            _PYFORGE_FONTS_DIR,
        ]
        ttf: Optional[Path] = None
        for d in candidates:
            for ext in (".ttf", ".otf"):
                # First try the slug-based name (what register_font may have copied there)
                for p in (d / f"{slug}_Regular{ext}", d / f"{slug}{ext}"):
                    if p.exists():
                        ttf = p
                        break
                if ttf:
                    break
                # Also scan directory for any file whose family name matches
                if d.exists():
                    for p in d.iterdir():
                        if p.suffix.lower() in (".ttf", ".otf"):
                            if _read_font_family(p) == family or _family_from_filename(p) == family:
                                ttf = p
                                break
            if ttf:
                break

        if ttf is None:
            logger.warning(
                "Custom font '%s' in config but no matching TTF found. "
                "Open Settings > Developer Options, re-scan, and reapply.",
                family,
            )
            return None

        if register_font(ttf):
            logger.info("Custom font '%s' loaded for this session", family)
            return family
        return None

    except Exception as exc:
        logger.error("load_custom_font: %s", exc)
        return None
