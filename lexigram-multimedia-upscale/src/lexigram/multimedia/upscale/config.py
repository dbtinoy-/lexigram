"""Configuration for the upscale generation subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class UpscaleConfig:
    backend: Literal["real-esrgan", "hat"] = "real-esrgan"
    real_esrgan_base_url: str = "http://localhost:5400"
    hat_base_url: str = "http://localhost:5401"
    default_scale_factor: Literal[2, 4] = 4
    timeout: float = 30.0


__all__ = ["UpscaleConfig"]
