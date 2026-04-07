"""Music generation package exceptions."""

from __future__ import annotations

from lexigram.contracts.multimedia.exceptions import MusicGenerationError

__all__ = [
    "MusicGenerationAuthenticationError",
    "MusicGenerationError",
    "MusicTimeoutError",
]


class MusicTimeoutError(MusicGenerationError):
    """Request exceeded the client timeout — recoverable by routing elsewhere.

    Not retried in place: the request already consumed a full timeout
    window, so the caller should advance to another provider. Mirrors
    lexigram-ai-llm's LLMTimeoutError fail-fast default.
    """

    _code = "LEX_ERR_MM_MUSIC_001"


class MusicGenerationAuthenticationError(MusicGenerationError):
    """Invalid API key or credentials — infrastructure error, raised not wrapped."""

    _code = "LEX_ERR_MM_MUSIC_002"
