"""Configuration for the interpolation subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class InterpolationConfig:
    backend: Literal["rife"] = "rife"
    rife_base_url: str = "http://localhost:5500"
    default_factor: Literal[2, 4] = 2
    timeout: float = 15.0


__all__ = ["InterpolationConfig"]
