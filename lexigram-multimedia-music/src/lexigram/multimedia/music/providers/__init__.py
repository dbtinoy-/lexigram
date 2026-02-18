"""Music provider backends."""

from __future__ import annotations

from lexigram.multimedia.music.providers.ace_step import AceStepMusicProvider
from lexigram.multimedia.music.providers.local_http import LocalHttpMusicProvider
from lexigram.multimedia.music.providers.stability_audio import (
    StabilityAudioMusicProvider,
)
from lexigram.multimedia.music.providers.stable_audio_open import (
    StableAudioOpenMusicProvider,
)

__all__ = [
    "AceStepMusicProvider",
    "LocalHttpMusicProvider",
    "StabilityAudioMusicProvider",
    "StableAudioOpenMusicProvider",
]
