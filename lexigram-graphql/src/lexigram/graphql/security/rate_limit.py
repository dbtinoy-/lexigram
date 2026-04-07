"""Rate limiting for GraphQL.

This module provides rate limiting for GraphQL operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from lexigram.config.base import BaseConfig
from lexigram.contracts.exceptions import RateLimitError as ContractsRateLimitError
from lexigram.contracts.web import WebRateLimiterProtocol
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class RateLimitConfig(BaseConfig):
    """Configuration for rate limiting.

    Attributes:
        enabled: Whether rate limiting is enabled.
        requests_per_minute: Number of allowed requests per minute.
        burst_limit: Maximum burst size.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = True
    requests_per_minute: int = Field(default=60, ge=1)
    burst_limit: int = Field(default=10, ge=1)


class RateLimiter:
    """Base class for rate limiters."""

    async def is_allowed(self, context: Any, **kwargs: Any) -> bool:
        """Check if a request is allowed."""
        return True


class UnifiedRateLimiter(RateLimiter):
    """Rate limiter that delegates to an injected web rate limiter."""

    def __init__(self, web_rate_limiter: WebRateLimiterProtocol | None = None) -> None:
        self._web_rate_limiter = web_rate_limiter

    async def is_allowed(self, context: Any, **kwargs: Any) -> bool:
        """Check if a request is allowed using the web rate limiter."""
        # Unpack kwargs
        max_requests = kwargs.get("max_requests", 60)
        window_seconds = kwargs.get("window_seconds", 60)
        scope = kwargs.get("scope", "user")

        if not hasattr(context, "raw_request") or not context.raw_request:
            return True

        if self._web_rate_limiter is None:
            return True

        try:
            await self._web_rate_limiter.check_rate_limit(
                context.raw_request,
                max_requests=max_requests,
                window_seconds=window_seconds,
                scope=scope,
            )
            return True
        except ContractsRateLimitError as exc:
            from lexigram.graphql.exceptions import RateLimitError

            raise RateLimitError("Rate limit exceeded") from exc
        except (LookupError, RuntimeError, AttributeError, TypeError, ValueError):
            # On infrastructure errors (Redis down, etc.) allow the request.
            return True


__all__ = [
    "RateLimitConfig",
    "RateLimiter",
    "UnifiedRateLimiter",
]
