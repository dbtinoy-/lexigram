"""Image and video super-resolution subsystem for the Lexigram multimedia package family."""

from __future__ import annotations

from lexigram.multimedia.upscale.config import UpscaleConfig
from lexigram.multimedia.upscale.di import UpscaleGenerationProvider
from lexigram.multimedia.upscale.module import UpscaleModule
from lexigram.multimedia.upscale.providers import (
    HatUpscaleProvider,
    RealEsrganUpscaleProvider,
)
from lexigram.multimedia.upscale.tasks import UpscaleTask
from lexigram.multimedia.upscale.video_upscale_service import VideoUpscaleService

__all__ = [
    "HatUpscaleProvider",
    "RealEsrganUpscaleProvider",
    "UpscaleConfig",
    "UpscaleGenerationProvider",
    "UpscaleModule",
    "UpscaleTask",
    "VideoUpscaleService",
]
