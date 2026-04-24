"""Interpolation package exceptions."""

from __future__ import annotations

from lexigram.contracts.multimedia.exceptions import MultimediaError

__all__ = ["InterpolationTimeoutError"]


class InterpolationTimeoutError(MultimediaError):
    """Request exceeded the client timeout — recoverable by routing elsewhere."""

    _code = "LEX_ERR_MM_INTERPOLATE_001"
