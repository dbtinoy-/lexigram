"""Umbrella configuration for the multimedia subsystem."""

from __future__ import annotations

from typing import ClassVar

from lexigram.config import BaseConfig
from lexigram.multimedia.beat.config import BeatAnalysisConfig
from lexigram.multimedia.image.config import ImageConfig
from lexigram.multimedia.interpolate.config import InterpolationConfig
from lexigram.multimedia.music.config import MusicConfig
from lexigram.multimedia.tts.config import TTSConfig
from lexigram.multimedia.upscale.config import UpscaleConfig
from lexigram.multimedia.video.config import VideoConfig
from lexigram.validation import Field


class MultimediaConfig(BaseConfig):
    """Umbrella configuration for the multimedia subsystem."""

    config_section: ClassVar[str] = "multimedia"
    tts: TTSConfig = Field(default_factory=TTSConfig)
    music: MusicConfig = Field(default_factory=MusicConfig)
    video: VideoConfig = Field(default_factory=VideoConfig)
    image: ImageConfig = Field(default_factory=ImageConfig)
    upscale: UpscaleConfig = Field(default_factory=UpscaleConfig)
    interpolate: InterpolationConfig = Field(default_factory=InterpolationConfig)
    beat: BeatAnalysisConfig = Field(default_factory=BeatAnalysisConfig)
    storage_path_prefix: str = "multimedia/"
    cache_results: bool = False


__all__ = ["MultimediaConfig"]
