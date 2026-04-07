"""Configuration for the music generation subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class MusicConfig:
    backend: Literal["local-http", "stability-audio"] = "local-http"
    local_http_base_url: str = "http://localhost:5003"
    duration_seconds: float = 30.0
    stability_api_key_secret_name: str = "stability_api_key"
    timeout: float = 60.0


__all__ = ["MusicConfig"]
