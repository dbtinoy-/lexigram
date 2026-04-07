"""HTTP-specific sanitization package for lexigram-web.

Contains header sanitization (CRLF injection prevention).
Transport-agnostic sanitization (HTML, URL, filename) lives in
``lexigram.security.sanitization`` (core).
"""

from __future__ import annotations

from lexigram.web.security.sanitization.header import HeaderSanitizer

__all__ = ["HeaderSanitizer"]
