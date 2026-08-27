"""Configuration for the image generation subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal

from lexigram.config import BaseConfig
from lexigram.contracts.core.config import Environment
from lexigram.validation import Field


@dataclass(init=False)
class ImageConfig(BaseConfig):
    """Configuration for the image generation subsystem."""

    config_section: ClassVar[str] = "multimedia_image"
    name: str = "multimedia_image"
    enabled: bool = True

    env: Environment | None = Field(None, description="Deployment environment")
    backend: Literal["local-http", "stability", "openai", "comfyui"] = "local-http"
    local_http_base_url: str = "http://localhost:5005"
    openai_api_key_secret_name: str = "openai_api_key"  # noqa: S105  # secret NAME, not a value
    openai_model: str = "dall-e-3"
    openai_base_url: str = "https://api.openai.com"
    stability_api_key_secret_name: str = "stability_api_key"  # noqa: S105  # secret NAME, not a value
    comfyui_base_url: str = "http://localhost:8188"
    comfyui_checkpoint: str = "sd_xl_base_1.0.safetensors"
    comfyui_workflow_path: str | None = None
    comfyui_steps: int = 20
    comfyui_cfg_scale: float = 7.0
    comfyui_poll_interval: float = 1.0
    timeout: float = 60.0


__all__ = ["ImageConfig"]
