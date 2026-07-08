"""Upscale generation package exceptions."""

from __future__ import annotations

from lexigram.contracts.multimedia.exceptions import UpscaleError

__all__ = [
    "UpscaleAssetTooLargeError",
    "UpscaleError",
    "UpscaleUnsafeAssetURLError",
]


class UpscaleAssetTooLargeError(UpscaleError, ValueError):
    """Raised when an upscale source asset exceeds the byte cap.

    Also a ``ValueError`` so callers and tests can treat the size-policy
    failure as plain validation.
    """

    _code = "LEX_ERR_MM_UPSCALE_001"

    def __init__(self, max_bytes: int) -> None:
        super().__init__(f"asset bytes too large: exceeds {max_bytes} byte cap")


class UpscaleUnsafeAssetURLError(UpscaleError, ValueError):
    """Raised when an upscale source asset URI is not safe to request.

    Also a ``ValueError`` so callers and tests can treat the URL-policy
    failure as plain validation.
    """

    _code = "LEX_ERR_MM_UPSCALE_002"

    def __init__(self, uri: str) -> None:
        super().__init__(f"unsafe asset URL: {uri!r}")
