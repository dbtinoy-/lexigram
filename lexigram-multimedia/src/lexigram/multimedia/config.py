"""Umbrella configuration for the multimedia subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field

from lexigram.multimedia.image.config import ImageConfig
from lexigram.multimedia.music.config import MusicConfig
from lexigram.multimedia.tts.config import TTSConfig
from lexigram.multimedia.video.config import VideoConfig


@dataclass
class MultimediaConfig:
    tts: TTSConfig = field(default_factory=TTSConfig)
    music: MusicConfig = field(default_factory=MusicConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    image: ImageConfig = field(default_factory=ImageConfig)
    storage_path_prefix: str = "multimedia/"
    cache_results: bool = False


__all__ = ["MultimediaConfig"]
