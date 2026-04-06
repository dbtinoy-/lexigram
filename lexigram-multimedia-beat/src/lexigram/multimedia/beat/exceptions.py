"""Beat-analysis package exceptions."""

from __future__ import annotations

from lexigram.contracts.multimedia.exceptions import BeatAnalysisError

__all__ = ["BeatAnalysisDecodeError", "BeatAnalysisError"]


class BeatAnalysisDecodeError(BeatAnalysisError):
    """Librosa could not decode the materialized audio file."""

    _code = "LEX_ERR_MM_BEAT_003"
