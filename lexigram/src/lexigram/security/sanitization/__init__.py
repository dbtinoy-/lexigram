"""Input sanitization package."""

from __future__ import annotations

from lexigram.security.config import InputSanitizerConfig
from lexigram.security.sanitization.sanitizer import InputSanitizer

__all__ = ["InputSanitizer", "InputSanitizerConfig"]
