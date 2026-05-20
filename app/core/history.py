"""Simple JSON-backed image history."""
from __future__ import annotations

import json
from pathlib import Path


def _history_file() -> Path:
    p = Path.home() / ".pyforge" / "history.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_history() -> list[dict]:
    f = _history_file()
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            return []
    return []


def add_to_history(paths: list[str], page: str) -> None:
    history = load_history()
    for p in paths:
        history.append({"path": p, "page": page})
    # Keep the last 500 entries
    _history_file().write_text(json.dumps(history[-500:], indent=2))
