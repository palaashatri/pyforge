from __future__ import annotations

import datetime
from pathlib import Path

from .config import config


def next_output_path(suffix: str = ".png") -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return config.outputs_dir / f"{ts}{suffix}"
