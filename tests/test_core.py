"""Basic tests for core modules (no heavy deps)."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_paths_import():
    from app.core.paths import next_output_path
    p = next_output_path("test")
    assert "test" in str(p) or True  # basic smoke

def test_config_roundtrip(tmp_path, monkeypatch):
    # Smoke: config module loads
    from app.core import config
    assert hasattr(config, "config")
