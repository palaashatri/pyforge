"""
Lazy-loaded diffusion pipelines.

All heavy imports (torch, diffusers) are deferred to the first call so the
UI window opens instantly even before any model is loaded.
"""
from __future__ import annotations

import base64
import io
import logging
import random
from pathlib import Path
from typing import Optional

from PIL import Image

from .manager import get_model_path
from .paths import next_output_path
from .config import config

logger = logging.getLogger(__name__)


# ── Lazy device/dtype helpers ─────────────────────────────────────────────────

def _torch():
    import torch
    return torch

def _device() -> str:
    pref = config.device
    if pref == "auto":
        torch = _torch()
        return "cuda" if torch.cuda.is_available() else "cpu"
    return pref

def _dtype():
    import torch
    return torch.float16 if _device() == "cuda" else torch.float32


# ── Pipeline cache ────────────────────────────────────────────────────────────
_cache: dict[str, object] = {}


def _load_txt2img(model_id: str):
    key = f"txt2img:{model_id}"
    if key not in _cache:
        from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline
        path = get_model_path(model_id)
        try:
            pipe = StableDiffusionXLPipeline.from_pretrained(
                str(path), torch_dtype=_dtype(), use_safetensors=True
            )
        except Exception:
            pipe = StableDiffusionPipeline.from_pretrained(
                str(path), torch_dtype=_dtype(), use_safetensors=True
            )
        pipe = pipe.to(_device())
        pipe.enable_attention_slicing()
        if config.xformers:
            pipe.enable_xformers_memory_efficient_attention()
        _cache[key] = pipe
        logger.info("Loaded txt2img pipeline for %s on %s", model_id, _device())
    return _cache[key]


def _load_img2img(model_id: str):
    key = f"img2img:{model_id}"
    if key not in _cache:
        from diffusers import StableDiffusionImg2ImgPipeline, StableDiffusionXLImg2ImgPipeline
        path = get_model_path(model_id)
        try:
            pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(
                str(path), torch_dtype=_dtype(), use_safetensors=True
            )
        except Exception:
            pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
                str(path), torch_dtype=_dtype(), use_safetensors=True
            )
        pipe = pipe.to(_device())
        pipe.enable_attention_slicing()
        if config.xformers:
            pipe.enable_xformers_memory_efficient_attention()
        _cache[key] = pipe
    return _cache[key]


def _load_inpaint(model_id: str):
    key = f"inpaint:{model_id}"
    if key not in _cache:
        from diffusers import StableDiffusionInpaintPipeline
        path = get_model_path(model_id)
        pipe = StableDiffusionInpaintPipeline.from_pretrained(
            str(path), torch_dtype=_dtype(), use_safetensors=True
        )
        pipe = pipe.to(_device())
        pipe.enable_attention_slicing()
        if config.xformers:
            pipe.enable_xformers_memory_efficient_attention()
        _cache[key] = pipe
    return _cache[key]


def _seed_generator(seed: int):
    import torch
    if seed == -1:
        seed = random.randint(0, 2**32 - 1)
    gen = torch.Generator(device=_device())
    gen.manual_seed(seed)
    return gen


def _save_images(images: list[Image.Image]) -> list[str]:
    paths = []
    fmt = config.image_format.upper()
    ext = ".jpg" if fmt.startswith("JPEG") else f".{fmt.lower()}"
    for img in images:
        out = next_output_path(ext)
        img.save(str(out), format=fmt.split()[0])
        paths.append(str(out))
    return paths


# ── Public generation functions ───────────────────────────────────────────────

def generate_txt2img(
    model_id: str,
    prompt: str,
    negative_prompt: str = "",
    width: int = 512,
    height: int = 512,
    steps: int = 25,
    cfg_scale: float = 7.5,
    seed: int = -1,
    batch_size: int = 1,
) -> list[str]:
    pipe = _load_txt2img(model_id)
    gen  = _seed_generator(seed)
    result = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt or None,
        width=width, height=height,
        num_inference_steps=steps,
        guidance_scale=cfg_scale,
        num_images_per_prompt=batch_size,
        generator=gen,
    )
    return _save_images(result.images)


def generate_img2img(
    model_id: str,
    prompt: str,
    input_image_path: str,
    negative_prompt: str = "",
    strength: float = 0.75,
    steps: int = 25,
    cfg_scale: float = 7.5,
    seed: int = -1,
) -> list[str]:
    pipe     = _load_img2img(model_id)
    init_img = Image.open(input_image_path).convert("RGB")
    gen      = _seed_generator(seed)
    result   = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt or None,
        image=init_img,
        strength=strength,
        num_inference_steps=steps,
        guidance_scale=cfg_scale,
        generator=gen,
    )
    return _save_images(result.images)


def generate_inpaint(
    model_id: str,
    prompt: str,
    input_image_path: str,
    mask_data_url: Optional[str] = None,
    mask_image_path: Optional[str] = None,
    steps: int = 25,
    cfg_scale: float = 7.5,
    seed: int = -1,
) -> list[str]:
    pipe     = _load_inpaint(model_id)
    init_img = Image.open(input_image_path).convert("RGB")

    if mask_data_url:
        _, b64 = mask_data_url.split(",", 1)
        mask_img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("L")
    elif mask_image_path:
        mask_img = Image.open(mask_image_path).convert("L")
    else:
        raise ValueError("Either mask_data_url or mask_image_path required")

    gen    = _seed_generator(seed)
    result = pipe(
        prompt=prompt,
        image=init_img,
        mask_image=mask_img,
        num_inference_steps=steps,
        guidance_scale=cfg_scale,
        generator=gen,
    )
    return _save_images(result.images)


def generate_upscale(
    model_id: str,
    input_image_path: str,
    scale_factor: int = 4,
) -> list[str]:
    try:
        import numpy as np
        from realesrgan import RealESRGANer
        from basicsr.archs.rrdbnet_arch import RRDBNet

        model_path_str = str(get_model_path(model_id))
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                        num_block=23, num_grow_ch=32, scale=scale_factor)
        upsampler = RealESRGANer(scale=scale_factor, model_path=model_path_str,
                                  model=model, half=_device() == "cuda")
        img = Image.open(input_image_path).convert("RGB")
        out_arr, _ = upsampler.enhance(np.array(img), outscale=scale_factor)
        out_img = Image.fromarray(out_arr)
    except ImportError:
        from diffusers import StableDiffusionUpscalePipeline
        pipe_key = f"upscale:{model_id}"
        if pipe_key not in _cache:
            path = get_model_path(model_id)
            pipe = StableDiffusionUpscalePipeline.from_pretrained(
                str(path), torch_dtype=_dtype()
            )
            pipe = pipe.to(_device())
            _cache[pipe_key] = pipe
        pipe    = _cache[pipe_key]
        lr      = Image.open(input_image_path).convert("RGB")
        result  = pipe(prompt="", image=lr)
        out_img = result.images[0]

    return _save_images([out_img])


def generate_controlnet(
    model_id: str,
    prompt: str,
    control_image_path: str,
    controlnet_type: str = "canny",
    conditioning_scale: float = 1.0,
    negative_prompt: str = "",
    width: int = 512,
    height: int = 512,
    steps: int = 25,
    cfg_scale: float = 7.5,
    seed: int = -1,
) -> list[str]:
    from diffusers import ControlNetModel, StableDiffusionControlNetPipeline

    cn_key = f"controlnet:{controlnet_type}"
    if cn_key not in _cache:
        cn_repo = {
            "canny":        "lllyasviel/sd-controlnet-canny",
            "depth":        "lllyasviel/sd-controlnet-depth",
            "pose":         "lllyasviel/sd-controlnet-openpose",
            "scribble":     "lllyasviel/sd-controlnet-scribble",
            "segmentation": "lllyasviel/sd-controlnet-seg",
            "normal map":   "lllyasviel/sd-controlnet-normal",
        }.get(controlnet_type.lower(), "lllyasviel/sd-controlnet-canny")
        _cache[cn_key] = ControlNetModel.from_pretrained(cn_repo, torch_dtype=_dtype())

    pipe_key = f"cn_pipe:{model_id}:{controlnet_type}"
    if pipe_key not in _cache:
        path = get_model_path(model_id)
        pipe = StableDiffusionControlNetPipeline.from_pretrained(
            str(path), controlnet=_cache[cn_key], torch_dtype=_dtype()
        )
        pipe = pipe.to(_device())
        pipe.enable_attention_slicing()
        if config.xformers:
            pipe.enable_xformers_memory_efficient_attention()
        _cache[pipe_key] = pipe

    pipe     = _cache[pipe_key]
    ctrl_img = Image.open(control_image_path).convert("RGB")
    gen      = _seed_generator(seed)
    result   = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt or None,
        image=ctrl_img,
        width=width, height=height,
        num_inference_steps=steps,
        guidance_scale=cfg_scale,
        controlnet_conditioning_scale=conditioning_scale,
        generator=gen,
    )
    return _save_images(result.images)
