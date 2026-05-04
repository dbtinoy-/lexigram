"""Beat-analysis package exceptions."""

from __future__ import annotations

from lexigram.contracts.multimedia.exceptions import BeatAnalysisError

__all__ = [
    "BeatAnalysisConnectionError",
    "BeatAnalysisDecodeError",
    "BeatAnalysisError",
    "BeatAnalysisTimeoutError",
]


class BeatAnalysisTimeoutError(BeatAnalysisError):
    """Madmom request exceeded the client timeout — recoverable by routing elsewhere."""

    _code = "LEX_ERR_MM_BEAT_001"


class BeatAnalysisConnectionError(BeatAnalysisError):
    """Madmom server unreachable — infrastructure error, raised not wrapped."""

    _code = "LEX_ERR_MM_BEAT_002"


class BeatAnalysisDecodeError(BeatAnalysisError):
    """Librosa could not decode the materialized audio file."""

    _code = "LEX_ERR_MM_BEAT_003"
