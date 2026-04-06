"""Text-to-speech generation subsystem for the Lexigram multimedia package family."""

from __future__ import annotations

from lexigram.multimedia.tts.config import TTSConfig
from lexigram.multimedia.tts.di import AudioTTSProvider
from lexigram.multimedia.tts.exceptions import TTSAuthenticationError
from lexigram.multimedia.tts.module import AudioTTSModule
from lexigram.multimedia.tts.providers import (
    ChatterboxTTSProvider,
    ElevenLabsTTSProvider,
    F5TTSProvider,
    KokoroTTSProvider,
    LocalHttpTTSProvider,
    OpenAITTSProvider,
    PiperTTSProvider,
)
from lexigram.multimedia.tts.tasks import TTSGenerationTask

__all__ = [
    "AudioTTSModule",
    "AudioTTSProvider",
    "ChatterboxTTSProvider",
    "ElevenLabsTTSProvider",
    "F5TTSProvider",
    "KokoroTTSProvider",
    "LocalHttpTTSProvider",
    "OpenAITTSProvider",
    "PiperTTSProvider",
    "TTSAuthenticationError",
    "TTSConfig",
    "TTSGenerationTask",
]
