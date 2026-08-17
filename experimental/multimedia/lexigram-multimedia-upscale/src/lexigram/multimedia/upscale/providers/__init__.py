"""Upscale provider backends."""

from __future__ import annotations

from lexigram.multimedia.upscale.providers.hat import HatUpscaleProvider
from lexigram.multimedia.upscale.providers.real_esrgan import RealEsrganUpscaleProvider

__all__ = ["HatUpscaleProvider", "RealEsrganUpscaleProvider"]
