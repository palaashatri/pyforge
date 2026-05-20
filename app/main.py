"""PyForge Studio — entry point."""
import sys
import os

# Ensure the project root is on sys.path so `app` is importable when
# running as `python app/main.py` or `python run.py` from the repo root.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app.ui.app_window import AppWindow


def main():
    win = AppWindow()
    win.mainloop()


if __name__ == "__main__":
    main()
