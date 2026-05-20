"""Colour palette and font helpers shared across all UI modules."""
import platform
import sys


def blend_hex(fg, bg, alpha: float):
    """Alpha-blend *fg* over *bg* at the given opacity (0–1).

    Accepts single hex strings OR ``(light, dark)`` colour tuples.
    Returns a tuple when either input is a tuple, a plain string otherwise.

    CTk accepts both forms for all colour parameters, so callers do not need
    to know which type they have — just pass the result directly to CTk.
    """
    # Tuple path — recurse once for each mode variant
    if isinstance(fg, tuple) or isinstance(bg, tuple):
        fg_l = fg[0] if isinstance(fg, tuple) else fg
        fg_d = fg[1] if isinstance(fg, tuple) else fg
        bg_l = bg[0] if isinstance(bg, tuple) else bg
        bg_d = bg[1] if isinstance(bg, tuple) else bg
        return (blend_hex(fg_l, bg_l, alpha), blend_hex(fg_d, bg_d, alpha))

    def _parse(h: str):
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    fr, fg_, fb = _parse(fg)
    br, bg_, bb = _parse(bg)
    r = int(fr * alpha + br * (1 - alpha))
    g = int(fg_ * alpha + bg_ * (1 - alpha))
    b = int(fb * alpha + bb * (1 - alpha))
    return f"#{r:02x}{g:02x}{b:02x}"


# ── Colour palette ────────────────────────────────────────────────────────────
# Every constant is a (light_mode, dark_mode) tuple.
#
# Passing tuples to CTk colour parameters lets ctk.set_appearance_mode() update
# every widget automatically — no widget rebuild required.
#
# Format: (light_colour, dark_colour)

# Backgrounds
BG         = ("#f4f4f9", "#0c0c12")
BG_PANEL   = ("#ffffff", "#14141e")
BG_CARD    = ("#ebebf5", "#1a1a26")
BG_INPUT   = ("#e3e3f0", "#20202e")
BG_HOVER   = ("#d8d8ec", "#282838")
BG_SIDEBAR = ("#eeeefc", "#0e0e16")

# Accent — vivid purple that reads well on both themes, same value both modes
ACCENT       = "#7c5cfc"
ACCENT_HOVER = "#9575ff"
ACCENT_DARK  = "#6244e8"

# Pre-blended tints (computed for both modes at import time)
ACCENT_TINT      = blend_hex(ACCENT, BG_SIDEBAR, 0.20)
ACCENT_TINT_CARD = blend_hex(ACCENT, BG_CARD,    0.20)

# Semantic
SUCCESS = ("#059669", "#34d399")   # darker on light bg; lighter on dark
DANGER  = ("#dc2626", "#f43f5e")
WARNING = ("#d97706", "#f59e0b")

# Text
TEXT       = ("#0a0a1a", "#f1f0f7")
TEXT_SEC   = ("#4a4870", "#9390a8")
TEXT_MUTED = ("#8888a8", "#5a5672")

# Borders
BORDER       = ("#d0d0e8", "#262638")
BORDER_LIGHT = ("#dcdcf0", "#32324a")


# ── Fonts ─────────────────────────────────────────────────────────────────────
_sys = platform.system()


def _pick_font() -> str:
    """Return the font face to use for all UI widgets.

    Priority:
    1. User-configured custom font (set in Settings > Developer Options).
    2. OS-appropriate system font (SF Pro Display / Segoe UI Variable / Noto Sans).
    """
    # 1. Check for a user-configured Google Font
    try:
        from ..core.config import config as _cfg
        family = _cfg.custom_font
        if family:
            return family
    except Exception:
        pass

    # 2. OS system font fallback
    if _sys == "Darwin":
        return "SF Pro Display"
    if _sys == "Windows":
        try:
            v = sys.getwindowsversion()
            # Windows 11 = NT 10.0, build >= 22000  ->  "Segoe UI Variable" is
            # a modern variable font that renders much sharper than "Segoe UI".
            if v.major >= 10 and v.build >= 22000:
                return "Segoe UI Variable"
        except Exception:
            pass
        return "Segoe UI"
    # Linux — Noto Sans is present on most modern distros
    return "Noto Sans"


FONT_FACE = _pick_font()


def font(size=13, bold=False):
    return (FONT_FACE, size, "bold") if bold else (FONT_FACE, size)


F_SM   = font(11)
F_MD   = font(13)
F_LG   = font(16)
F_XL   = font(20)
F_SM_B = font(11, bold=True)
F_MD_B = font(13, bold=True)
F_LG_B = font(16, bold=True)
