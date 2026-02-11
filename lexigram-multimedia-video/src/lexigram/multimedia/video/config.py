"""Configuration for the video generation subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class VideoProcessingConfig:
    ffmpeg_binary: str = "ffmpeg"
    max_concurrent_jobs: int = 2
    temp_dir: str | None = None
    timeout: float = 300.0


@dataclass
class VideoConfig:
    backend: Literal[
        "local-http",
        "runway",
        "openai",
        "wan22",
        "cogvideox",
        "svd",
        "comfyui",
    ] = "local-http"
    local_http_base_url: str = "http://localhost:5004"
    runway_api_key_secret_name: str = "runway_api_key"
    openai_api_key_secret_name: str = "openai_api_key"
    openai_model: str = "sora-2"
    openai_base_url: str = "https://api.openai.com"
    wan22_base_url: str = "http://localhost:5200"
    cogvideox_base_url: str = "http://localhost:5201"
    svd_base_url: str = "http://localhost:5202"
    comfyui_base_url: str = "http://localhost:8188"
    comfyui_checkpoint: str = "svd_xt_1_1.safetensors"
    comfyui_workflow_path: str | None = None
    comfyui_fps: int = 6
    comfyui_motion_bucket_id: int = 127
    comfyui_poll_interval: float = 1.0
    timeout: float = 60.0
    processing: VideoProcessingConfig = field(default_factory=VideoProcessingConfig)


__all__ = ["VideoConfig", "VideoProcessingConfig"]
