"""Music generation package exceptions."""

from __future__ import annotations

from lexigram.contracts.multimedia.exceptions import MusicGenerationError

__all__ = ["MusicGenerationAuthenticationError", "MusicGenerationError"]


class MusicGenerationAuthenticationError(MusicGenerationError):
    """Raised when the music backend rejects the configured API credentials."""

    _code = "LEX_ERR_MM_MUSIC_001"
