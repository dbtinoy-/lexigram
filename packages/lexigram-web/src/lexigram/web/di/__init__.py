"""Framework integration for lexigram-web."""

from __future__ import annotations

from lexigram.web.di.provider import WebProvider
from lexigram.web.di.rate_limit import RateLimitProvider
from lexigram.web.integrations.setup import lifespan

__all__ = ["RateLimitProvider", "WebProvider", "lifespan"]
