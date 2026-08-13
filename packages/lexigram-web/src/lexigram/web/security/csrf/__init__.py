"""CSRF protection package for lexigram-web."""

from __future__ import annotations

from lexigram.web.security.config import CSRFConfig
from lexigram.web.security.csrf.middleware import CSRFProtectionMiddleware

__all__ = ["CSRFConfig", "CSRFProtectionMiddleware"]
