"""Security response headers package for lexigram-web."""

from __future__ import annotations

from lexigram.web.security.config import SecurityHeadersConfig
from lexigram.web.security.headers.middleware import SecurityHeadersMiddleware

__all__ = ["SecurityHeadersConfig", "SecurityHeadersMiddleware"]
