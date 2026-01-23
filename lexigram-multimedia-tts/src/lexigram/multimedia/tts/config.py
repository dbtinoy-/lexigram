"""Configuration for the TTS subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class TTSConfig:
    backend: Literal["local-http", "elevenlabs", "openai"] = "local-http"
    local_http_base_url: str = "http://localhost:5002"
    elevenlabs_voice_id: str | None = None
    elevenlabs_api_key_secret_name: str = "elevenlabs_api_key"
    openai_api_key_secret_name: str = "openai_api_key"
    timeout: float = 60.0


__all__ = ["TTSConfig"]
