"""CORS configuration and middleware package for lexigram-web."""

from __future__ import annotations

from lexigram.web.security.config import CORSConfig
from lexigram.web.security.cors.middleware import CORSMiddleware

__all__ = ["CORSConfig", "CORSMiddleware"]
