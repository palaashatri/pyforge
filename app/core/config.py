from __future__ import annotations

import json
import sys
from pathlib import Path


def _models_dir() -> Path:
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Local" / "PyForge"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "PyForge"
    else:
        base = Path.home() / ".local" / "share" / "pyforge"
    return base / "models"


def _outputs_dir() -> Path:
    return Path.home() / ".pyforge" / "outputs"


def _config_file() -> Path:
    return Path.home() / ".pyforge" / "config.json"


class Config:
    def __init__(self) -> None:
        self._file = _config_file()
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        if self._file.exists():
            try:
                self._data = json.loads(self._file.read_text())
            except Exception:
                self._data = {}

    def save(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._file.write_text(json.dumps(self._data, indent=2))

    @property
    def models_dir(self) -> Path:
        p = Path(self._data.get("models_dir", str(_models_dir())))
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def outputs_dir(self) -> Path:
        p = Path(self._data.get("outputs_dir", str(_outputs_dir())))
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def device(self) -> str:
        return self._data.get("device", "auto")

    @property
    def image_format(self) -> str:
        return self._data.get("image_format", "PNG")

    @property
    def xformers(self) -> bool:
        return self._data.get("xformers", False)

    @property
    def theme(self) -> str:
        return self._data.get("theme", "dark")

    @property
    def custom_font(self) -> str:
        """Font family name for the UI (empty string = use OS system font)."""
        return self._data.get("custom_font", "")

    def update(self, **kwargs) -> None:
        self._data.update(kwargs)
        self.save()

    def as_dict(self) -> dict:
        return {
            "device":       self.device,
            "xformers":     self.xformers,
            "image_format": self.image_format,
            "outputs_dir":  str(self.outputs_dir),
            "theme":        self.theme,
            "custom_font":  self.custom_font,
        }


config = Config()
