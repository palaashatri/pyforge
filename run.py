"""Quick launcher — run from the repo root: python run.py"""
import sys

# Windows: Per-Monitor DPI awareness makes the window crisp on HiDPI / scaled
# displays instead of letting Windows stretch a lower-DPI render.
# Must be called before any Tk or CTk window is created.
if sys.platform == "win32":
    try:
        import ctypes
        try:
            # SetProcessDpiAwareness(2) = PROCESS_PER_MONITOR_DPI_AWARE
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            # Older Windows fallback (Vista+)
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

from app.main import main

if __name__ == "__main__":
    main()
