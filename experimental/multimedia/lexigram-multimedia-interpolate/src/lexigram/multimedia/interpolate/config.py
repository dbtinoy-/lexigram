"""Configuration for the interpolation subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal

from lexigram.config import BaseConfig


@dataclass(init=False)
class InterpolationConfig(BaseConfig):
    """Configuration for the interpolation subsystem."""

    config_section: ClassVar[str] = "multimedia_interpolate"
    backend: Literal["rife"] = "rife"
    rife_base_url: str = "http://localhost:5500"
    timeout: float = 15.0


__all__ = ["InterpolationConfig"]
