"""Configuration for the image generation subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class ImageConfig:
    backend: Literal["local-http", "stability"] = "local-http"
    local_http_base_url: str = "http://localhost:5005"
    openai_api_key_secret_name: str = "openai_api_key"
    stability_api_key_secret_name: str = "stability_api_key"
    timeout: float = 60.0


__all__ = ["ImageConfig"]
