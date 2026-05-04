"""TTS provider backends."""

from __future__ import annotations

from lexigram.multimedia.tts.providers.chatterbox import ChatterboxTTSProvider
from lexigram.multimedia.tts.providers.elevenlabs import ElevenLabsTTSProvider
from lexigram.multimedia.tts.providers.f5_tts import F5TTSProvider
from lexigram.multimedia.tts.providers.kokoro import KokoroTTSProvider
from lexigram.multimedia.tts.providers.local_http import LocalHttpTTSProvider
from lexigram.multimedia.tts.providers.openai import OpenAITTSProvider
from lexigram.multimedia.tts.providers.piper import PiperTTSProvider

__all__ = [
    "ChatterboxTTSProvider",
    "ElevenLabsTTSProvider",
    "F5TTSProvider",
    "KokoroTTSProvider",
    "LocalHttpTTSProvider",
    "OpenAITTSProvider",
    "PiperTTSProvider",
]
