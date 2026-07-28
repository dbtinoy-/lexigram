"""Rate limiting integration for WebProvider."""

from __future__ import annotations

from typing import Any, cast

from starlette.applications import Starlette

from lexigram.contracts.exceptions import RateLimitError
from lexigram.contracts.web import WebRateLimiterProtocol
from lexigram.di.container import Container
from lexigram.logging import get_logger
from lexigram.web.middleware.rate_limit import (
    RateLimiter,
    RateLimitMiddleware,
)

logger = get_logger(__name__)


class RateLimitIntegration:
    """Handles rate limit middleware and handler configuration."""

    @staticmethod
    async def configure(app: Starlette, container: Container, web_config: Any) -> None:
        """Configure rate limit middleware and handlers."""
        if (
            not getattr(web_config, "rate_limit", None)
            or not web_config.rate_limit.enabled
        ):
            return

        rate_limiter = None
        try:
            # Try to resolve by protocol
            rate_limiter = await container.resolve(cast("Any", WebRateLimiterProtocol))
        except Exception as err:  # noqa: BLE001 — optional service; any resolution failure falls back to in-memory
            logger.info("Using in-memory RateLimiter fallback: %r", err)
            rate_limiter = RateLimiter()

        if rate_limiter:
            app.add_exception_handler(
                RateLimitError,
                RateLimitIntegration._rate_limit_handler,
            )
            app.add_middleware(
                RateLimitMiddleware, rate_limiter=cast("Any", rate_limiter)
            )
            logger.info("Rate limiting middleware configured")

    @staticmethod
    async def _rate_limit_handler(_request: Any, exc: Exception) -> Any:
        """Standard rate limit exceeded handler."""
        from starlette.responses import JSONResponse

        details = getattr(exc, "details", {}) or {}
        retry_after = details.get("retry_after")
        return JSONResponse(
            {"error": "rate_limit_exceeded", "message": str(exc)},
            status_code=429,
            headers={"Retry-After": str(retry_after)} if retry_after else {},
        )
