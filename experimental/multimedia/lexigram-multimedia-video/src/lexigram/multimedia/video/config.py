"""Configuration for the video generation subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal

from lexigram.config import BaseConfig
from lexigram.contracts.core.config import Environment
from lexigram.validation import Field


@dataclass(init=False)
class VideoProcessingConfig(BaseConfig):
    """Configuration for the local FFmpeg video-processing pipeline."""

    config_section: ClassVar[str] = "multimedia_video_processing"
    name: str = "multimedia_video_processing"
    enabled: bool = True

    env: Environment | None = Field(None, description="Deployment environment")
    ffmpeg_binary: str = "ffmpeg"
    max_concurrent_jobs: int = 2
    temp_dir: str | None = None
    timeout: float = 300.0
    max_asset_bytes: int = 25 * 1024 * 1024


@dataclass(init=False)
class VideoConfig(BaseConfig):
    """Configuration for the video generation subsystem."""

    config_section: ClassVar[str] = "multimedia_video"
    name: str = "multimedia_video"
    enabled: bool = True

    env: Environment | None = Field(None, description="Deployment environment")
    backend: Literal[
        "local-http", "runway", "openai", "wan22", "cogvideox", "svd", "comfyui"
    ] = "local-http"
    local_http_base_url: str = "http://localhost:5004"
    runway_api_key_secret_name: str = "runway_api_key"  # noqa: S105  # secret NAME, not a value
    openai_api_key_secret_name: str = "openai_api_key"  # noqa: S105  # secret NAME, not a value
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
    timeout: float | None = None
    processing: VideoProcessingConfig = Field(default_factory=VideoProcessingConfig)


__all__ = ["VideoConfig", "VideoProcessingConfig"]
