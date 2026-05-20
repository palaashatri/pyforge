from __future__ import annotations

import json
import logging
import shutil
import time
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from huggingface_hub import snapshot_download, HfApi

from .config import config

logger = logging.getLogger(__name__)

_REGISTRY_FILE = "registry.json"


@dataclass
class ModelInfo:
    model_id: str          # slug used as directory name
    repo_id: str           # HuggingFace repo, e.g. "runwayml/stable-diffusion-v1-5"
    alias: Optional[str]   # human-readable name
    type: str              # "SD1.5" | "SDXL" | "Flux" | "unknown"
    size_gb: Optional[float]

    def to_dict(self) -> dict:
        return asdict(self)


def _registry_path() -> Path:
    return config.models_dir / _REGISTRY_FILE


def _load_registry() -> dict[str, dict]:
    p = _registry_path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def _save_registry(reg: dict[str, dict]) -> None:
    _registry_path().write_text(json.dumps(reg, indent=2))


def _detect_type(repo_id: str) -> str:
    r = repo_id.lower()
    if "flux" in r:
        return "Flux"
    if "xl" in r or "sdxl" in r:
        return "SDXL"
    if "stable-diffusion" in r or "sd" in r:
        return "SD1.5"
    return "unknown"


def _dir_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _dir_size_gb(path: Path) -> float:
    return round(_dir_size_bytes(path) / 1e9, 2)


def list_models() -> list[ModelInfo]:
    reg = _load_registry()
    result = []
    for model_id, meta in reg.items():
        model_dir = config.models_dir / model_id
        if model_dir.exists():
            result.append(ModelInfo(**meta))
    return result


def download_model(
    repo_id: str,
    alias: Optional[str] = None,
    token: Optional[str] = None,
    progress: Optional[dict] = None,
) -> ModelInfo:
    """
    Download a model from HuggingFace.

    Pass a shared ``progress`` dict to get live updates while the download
    runs in a background thread.  The dict will have these keys set:
        progress    float 0-1
        message     str
        speed_mbps  float
        eta_seconds int
        done        bool   (True when complete or errored)
        error       str | None
    """
    model_id = repo_id.replace("/", "--")
    dest = config.models_dir / model_id
    dest.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading %s to %s", repo_id, dest)

    # Fetch total size from HuggingFace API (best-effort)
    total_bytes = 0
    try:
        api = HfApi()
        repo_info = api.repo_info(repo_id, token=token)
        if repo_info and hasattr(repo_info, "siblings") and repo_info.siblings:
            total_bytes = sum(f.size or 0 for f in repo_info.siblings)
    except Exception as e:
        logger.warning("Could not fetch repo size: %s", e)

    start_time = time.time()
    last_bytes = [0]
    last_time  = [start_time]
    stop_poll  = threading.Event()

    def _poll():
        while not stop_poll.is_set():
            current_bytes = _dir_size_bytes(dest)
            now     = time.time()
            elapsed = now - last_time[0]
            delta   = current_bytes - last_bytes[0]
            speed   = delta / elapsed if elapsed > 0 else 0

            if total_bytes > 0:
                prog = min(current_bytes / total_bytes, 0.99)
                eta  = int((total_bytes - current_bytes) / speed) if speed > 0 else 0
                msg  = (
                    f"Downloading {repo_id} — "
                    f"{current_bytes/1e9:.2f} / {total_bytes/1e9:.2f} GB  "
                    f"({speed/1e6:.1f} MB/s)"
                )
            else:
                prog = 0.0
                eta  = 0
                msg  = f"Downloading {repo_id} — {current_bytes/1e9:.2f} GB"

            if progress is not None:
                progress.update(progress=round(prog, 4),
                                speed_mbps=round(speed / 1e6, 2),
                                eta_seconds=eta,
                                message=msg,
                                done=False, error=None)

            last_bytes[0] = current_bytes
            last_time[0]  = now
            time.sleep(0.5)

    poll_thread = threading.Thread(target=_poll, daemon=True)
    poll_thread.start()

    try:
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(dest),
            token=token,
            ignore_patterns=["*.msgpack", "*.h5", "flax_model*"],
        )
    finally:
        stop_poll.set()
        poll_thread.join(timeout=2)

    info = ModelInfo(
        model_id=model_id,
        repo_id=repo_id,
        alias=alias or repo_id.split("/")[-1],
        type=_detect_type(repo_id),
        size_gb=_dir_size_gb(dest),
    )

    reg = _load_registry()
    reg[model_id] = info.to_dict()
    _save_registry(reg)

    if progress is not None:
        progress.update(progress=1.0, message="Download complete!",
                        speed_mbps=0, eta_seconds=0, done=True, error=None)

    logger.info("Registered model %s", model_id)
    return info


def is_model_installed(repo_id: str) -> bool:
    """Return True if *repo_id* is already in the local registry."""
    model_id = repo_id.replace("/", "--")
    reg = _load_registry()
    return model_id in reg and (config.models_dir / model_id).exists()


def _hf_version() -> str:
    try:
        import importlib.metadata
        return importlib.metadata.version("huggingface_hub")
    except Exception:
        return "unknown"


def _parse_hub_models(raw: list) -> list[dict]:
    result = []
    for m in raw:
        # .id in huggingface_hub >= 0.19;  .modelId in older releases
        rid = getattr(m, "id", None) or getattr(m, "modelId", "")
        if not rid:
            continue
        parts = rid.split("/", 1)
        result.append({
            "repo_id":   rid,
            "name":      parts[1] if len(parts) > 1 else rid,
            "author":    parts[0] if len(parts) > 1 else "",
            "downloads": getattr(m, "downloads", 0) or 0,
            "likes":     getattr(m, "likes", 0) or 0,
        })
    return result


def browse_hub_models(
    task: str = "text-to-image",
    limit: int = 40,
    token: Optional[str] = None,
) -> list[dict]:
    """Return the most-downloaded *task* models from HuggingFace Hub.

    Tries three calling conventions to cover huggingface_hub 0.11 – 1.x:
      1. pipeline_tag= (1.x — direction= removed, sort descends by default)
      2. pipeline_tag= + direction=-1 (0.18 – 0.x)
      3. filter=ModelFilter(task=) (0.11 – 0.17)

    Raises ``RuntimeError`` with a human-readable message on failure.
    """
    from huggingface_hub import list_models as _hf_list

    last_err: Exception | None = None

    # Strategy 1 — huggingface_hub >= 1.0  (direction param removed)
    try:
        raw = list(_hf_list(
            pipeline_tag=task, sort="downloads", limit=limit, token=token,
        ))
        return _parse_hub_models(raw)
    except TypeError as exc:
        last_err = exc

    # Strategy 2 — huggingface_hub 0.18 – 0.x  (has direction=)
    try:
        raw = list(_hf_list(
            pipeline_tag=task, sort="downloads", direction=-1,
            limit=limit, token=token,
        ))
        return _parse_hub_models(raw)
    except TypeError as exc:
        last_err = exc

    # Strategy 3 — huggingface_hub 0.11 – 0.17  (ModelFilter API)
    try:
        from huggingface_hub import ModelFilter
        raw = list(_hf_list(
            filter=ModelFilter(task=task),
            sort="downloads", direction=-1, limit=limit, token=token,
        ))
        return _parse_hub_models(raw)
    except Exception as exc:
        last_err = exc

    raise RuntimeError(
        f"Could not query HuggingFace Hub.\n"
        f"huggingface_hub {_hf_version()} — no compatible list_models() API found.\n"
        f"Last error: {last_err}\n\n"
        f"Fix: pip install --upgrade huggingface_hub"
    )


def run_diagnostics() -> list[dict]:
    """Run environment checks.  Returns list of dicts with keys:
    section, label, value, status  ('ok' | 'error' | 'warn' | 'info').
    """
    import sys, platform, importlib.metadata

    out: list[dict] = []

    def row(section, label, value, status="info"):
        out.append({"section": section, "label": label, "value": str(value), "status": status})

    # ── System ────────────────────────────────────────────────────────────────
    row("System", "Python",   f"{sys.version.split()[0]}  ({platform.architecture()[0]})")
    row("System", "OS",       f"{platform.system()} {platform.release()}  ({platform.machine()})")

    # ── Packages ──────────────────────────────────────────────────────────────
    _required = {"huggingface_hub", "diffusers", "transformers", "customtkinter", "Pillow"}
    _optional = {"torch", "accelerate", "xformers", "realesrgan"}
    for pkg in sorted(_required | _optional):
        try:
            ver = importlib.metadata.version(pkg)
            row("Packages", pkg, ver, "ok")
        except importlib.metadata.PackageNotFoundError:
            status = "warn" if pkg in _optional else "error"
            row("Packages", pkg, "not installed", status)

    # ── HuggingFace ───────────────────────────────────────────────────────────
    row("HuggingFace", "hub version", _hf_version())

    # Basic connectivity — minimal call, no filters
    try:
        from huggingface_hub import list_models as _hf_list
        list(_hf_list(limit=1))
        row("HuggingFace", "API reachable", "Yes", "ok")
    except Exception as exc:
        row("HuggingFace", "API reachable", str(exc), "error")

    # Full catalog fetch
    try:
        models = browse_hub_models(limit=3)
        row("HuggingFace", "browse_hub_models()", f"OK — {len(models)} results", "ok")
    except Exception as exc:
        row("HuggingFace", "browse_hub_models()", str(exc), "error")

    # ── GPU ───────────────────────────────────────────────────────────────────
    try:
        import torch
        row("GPU", "torch version", torch.__version__)
        if torch.cuda.is_available():
            dev  = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / 1e9
            row("GPU", "CUDA device", f"{dev}  ({vram:.1f} GB VRAM)", "ok")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            row("GPU", "MPS (Apple Silicon)", "Available", "ok")
        else:
            row("GPU", "GPU acceleration", "Not available — CPU only", "warn")
    except ImportError:
        row("GPU", "torch", "Not installed — GPU info unavailable", "error")
    except Exception as exc:
        row("GPU", "Error", str(exc), "error")

    return out


def delete_model(model_id: str) -> None:
    dest = config.models_dir / model_id
    if dest.exists():
        shutil.rmtree(dest)
    reg = _load_registry()
    reg.pop(model_id, None)
    _save_registry(reg)
    logger.info("Deleted model %s", model_id)


def get_model_path(model_id: str) -> Path:
    path = config.models_dir / model_id
    if not path.exists():
        raise FileNotFoundError(f"Model '{model_id}' not found at {path}")
    return path
