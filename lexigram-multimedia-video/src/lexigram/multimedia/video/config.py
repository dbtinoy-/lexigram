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
    backend: Literal["local-http", "runway"] = "local-http"
    local_http_base_url: str = "http://localhost:5004"
    runway_api_key_secret_name: str = "runway_api_key"
    openai_api_key_secret_name: str = "openai_api_key"
    timeout: float = 60.0
    processing: VideoProcessingConfig = field(default_factory=VideoProcessingConfig)
