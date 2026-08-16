from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RateLimiterStats:
    """Statistics for rate limiter performance."""

    total_requests: int = 0
    allowed_requests: int = 0
    denied_requests: int = 0
    total_wait_time: float = 0.0
