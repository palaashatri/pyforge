"""Colour palette and font helpers shared across all UI modules."""
import platform
import sys


def blend_hex(fg: str, bg: str, alpha: float) -> str:
    """Alpha-blend *fg* over *bg* at the given opacity (0–1) and return a
    6-digit ``#RRGGBB`` string.  Tkinter/Tk does not support 8-digit hex or
    any rgba notation, so every semi-transparent colour must be pre-blended."""
    def _parse(h: str):
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    fr, fg_, fb = _parse(fg)
    br, bg_, bb = _parse(bg)
    r = int(fr * alpha + br * (1 - alpha))
    g = int(fg_ * alpha + bg_ * (1 - alpha))
    b = int(fb * alpha + bb * (1 - alpha))
    return f"#{r:02x}{g:02x}{b:02x}"


# ── Backgrounds ──────────────────────────────────────────────────────────────
BG          = "#0c0c12"
BG_PANEL    = "#14141e"
BG_CARD     = "#1a1a26"
BG_INPUT    = "#20202e"
BG_HOVER    = "#282838"
BG_SIDEBAR  = "#0e0e16"

# ── Accent (purple) ───────────────────────────────────────────────────────────
ACCENT       = "#7c5cfc"
ACCENT_HOVER = "#9575ff"
ACCENT_DARK  = "#6244e8"

# Pre-blended tints — use these wherever you'd want "ACCENT at ~20% opacity".
# Tk only accepts 6-digit #RRGGBB; no alpha channel support.
ACCENT_TINT         = blend_hex(ACCENT, BG_SIDEBAR, 0.20)  # for sidebar rows
ACCENT_TINT_CARD    = blend_hex(ACCENT, BG_CARD,    0.20)  # for card icon badges

# ── Semantic ──────────────────────────────────────────────────────────────────
SUCCESS = "#34d399"
DANGER  = "#f43f5e"
WARNING = "#f59e0b"

# ── Text ──────────────────────────────────────────────────────────────────────
TEXT       = "#f1f0f7"
TEXT_SEC   = "#9390a8"
TEXT_MUTED = "#5a5672"

# ── Borders ───────────────────────────────────────────────────────────────────
BORDER       = "#262638"
BORDER_LIGHT = "#32324a"

# ── Fonts ─────────────────────────────────────────────────────────────────────
_sys = platform.system()


def _pick_font() -> str:
    """Return the best available font face for this OS / version."""
    if _sys == "Darwin":
        return "SF Pro Display"
    if _sys == "Windows":
        try:
            v = sys.getwindowsversion()
            # Windows 11 = NT 10.0, build >= 22000  →  "Segoe UI Variable" is
            # a modern variable font that renders much sharper than "Segoe UI".
            if v.major >= 10 and v.build >= 22000:
                return "Segoe UI Variable"
        except Exception:
            pass
        return "Segoe UI"
    # Linux — "Noto Sans" is present on most modern distros; Tk falls back
    # gracefully to its default if the font is not installed.
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
