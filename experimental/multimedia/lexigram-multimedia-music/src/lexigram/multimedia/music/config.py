"""Configuration for the music generation subsystem."""

from __future__ import annotations

from typing import ClassVar, Literal

from lexigram.config import BaseConfig


class MusicConfig(BaseConfig):
    """Configuration for the music generation subsystem."""

    config_section: ClassVar[str] = "multimedia_music"
    backend: Literal[
        "local-http", "stability-audio", "ace-step", "stable-audio-open"
    ] = "local-http"
    local_http_base_url: str = "http://localhost:5003"
    ace_step_base_url: str = "http://localhost:5300"
    stable_audio_open_base_url: str = "http://localhost:5301"
    stability_api_key_secret_name: str = "stability_api_key"  # noqa: S105  # secret NAME, not a value
    timeout: float = 60.0


__all__ = ["MusicConfig"]
