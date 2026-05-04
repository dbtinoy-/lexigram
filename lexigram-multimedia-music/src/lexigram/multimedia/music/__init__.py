"""Music generation subsystem for the Lexigram multimedia package family."""

from __future__ import annotations

from lexigram.multimedia.music.config import MusicConfig
from lexigram.multimedia.music.di import AudioMusicProvider
from lexigram.multimedia.music.exceptions import (
    MusicGenerationAuthenticationError,
    MusicTimeoutError,
)
from lexigram.multimedia.music.module import AudioMusicModule
from lexigram.multimedia.music.providers import (
    AceStepMusicProvider,
    LocalHttpMusicProvider,
    StabilityAudioMusicProvider,
    StableAudioOpenMusicProvider,
)
from lexigram.multimedia.music.tasks import MusicGenerationTask

__all__ = [
    "AceStepMusicProvider",
    "AudioMusicModule",
    "AudioMusicProvider",
    "LocalHttpMusicProvider",
    "MusicConfig",
    "MusicGenerationAuthenticationError",
    "MusicGenerationTask",
    "MusicTimeoutError",
    "StabilityAudioMusicProvider",
    "StableAudioOpenMusicProvider",
]
