"""Image generation exceptions for the lexigram-multimedia-image package."""

from __future__ import annotations

from lexigram.contracts.multimedia.exceptions import ImageGenerationError

__all__ = [
    "ImageGenerationAuthenticationError",
    "ImageGenerationError",
    "ImageTimeoutError",
]


class ImageTimeoutError(ImageGenerationError):
    """Raised when an image generation operation exceeds its timeout."""

    _code = "LEX_ERR_MM_IMAGE_001"


class ImageGenerationAuthenticationError(ImageGenerationError):
    """Raised when the image backend rejects the configured API credentials."""

    _code = "LEX_ERR_MM_IMAGE_002"
