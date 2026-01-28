"""Upscale generation package exceptions."""

from __future__ import annotations

from lexigram.contracts.multimedia.exceptions import UpscaleError

__all__ = ["UpscaleError", "UpscaleTimeoutError"]


class UpscaleTimeoutError(UpscaleError):
    """Request exceeded the client timeout — recoverable by routing elsewhere."""

    _code = "LEX_ERR_MM_UPSCALE_001"
