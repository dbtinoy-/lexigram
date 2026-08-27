"""Configuration for the TTS subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal

from lexigram.config import BaseConfig
from lexigram.contracts.core.config import Environment
from lexigram.validation import Field


@dataclass(init=False)
class TTSConfig(BaseConfig):
    """Configuration for the TTS subsystem."""

    config_section: ClassVar[str] = "multimedia_tts"
    name: str = "multimedia_tts"
    enabled: bool = True

    env: Environment | None = Field(None, description="Deployment environment")
    backend: Literal[
        "local-http", "elevenlabs", "openai", "chatterbox", "kokoro", "f5-tts", "piper"
    ] = "local-http"
    local_http_base_url: str = "http://localhost:5002"
    elevenlabs_voice_id: str | None = None
    elevenlabs_api_key_secret_name: str = "elevenlabs_api_key"  # noqa: S105  # secret NAME, not a value
    openai_api_key_secret_name: str = "openai_api_key"  # noqa: S105  # secret NAME, not a value
    openai_voice: str = "alloy"
    openai_model: str = "tts-1"
    openai_base_url: str = "https://api.openai.com"
    chatterbox_base_url: str = "http://localhost:5100"
    chatterbox_exaggeration: float = 0.5
    chatterbox_cfg_weight: float = 0.5
    chatterbox_temperature: float = 0.85
    kokoro_base_url: str = "http://localhost:5101"
    kokoro_default_voice: str = "af_heart"
    f5_tts_base_url: str = "http://localhost:5102"
    piper_base_url: str = "http://localhost:5103"
    piper_default_voice: str = "en_US-lessac-medium"
    timeout: float = 60.0


__all__ = ["TTSConfig"]
