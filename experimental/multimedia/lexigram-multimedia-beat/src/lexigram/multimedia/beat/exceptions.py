"""Beat-analysis package exceptions."""

from __future__ import annotations

from lexigram.contracts.multimedia.exceptions import BeatAnalysisError

__all__ = ["BeatAnalysisDecodeError", "BeatAnalysisError"]


class BeatAnalysisDecodeError(BeatAnalysisError):
    """Audio could not be decoded, or was rejected before decoding.

    Covers undecodable files, unsafe asset URIs, payloads over the
    ``max_asset_bytes`` cap, probed durations over the
    ``max_analyze_samples`` ceiling, and decoded arrays over the
    ``max_analyze_samples`` ceiling.
    """

    _code = "LEX_ERR_MM_BEAT_003"
