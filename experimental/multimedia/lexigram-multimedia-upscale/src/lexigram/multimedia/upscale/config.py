"""Configuration for the upscale generation subsystem."""

from __future__ import annotations

from typing import ClassVar, Literal

from lexigram.config import BaseConfig


class UpscaleConfig(BaseConfig):
    """Configuration for the upscale generation subsystem."""

    config_section: ClassVar[str] = "multimedia_upscale"
    backend: Literal["real-esrgan", "hat"] = "real-esrgan"
    real_esrgan_base_url: str = "http://localhost:5400"
    hat_base_url: str = "http://localhost:5401"
    timeout: float = 30.0


__all__ = ["UpscaleConfig"]
