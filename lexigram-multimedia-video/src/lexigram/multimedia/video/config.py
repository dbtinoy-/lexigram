"""Configuration for the video generation subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class VideoConfig:
    backend: Literal["local-http", "runway"] = "local-http"
    local_http_base_url: str = "http://localhost:5004"
    runway_api_key_secret_name: str = "runway_api_key"
    openai_api_key_secret_name: str = "openai_api_key"
    timeout: float = 60.0
