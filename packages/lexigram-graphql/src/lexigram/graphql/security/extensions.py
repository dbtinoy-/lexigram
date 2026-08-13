"""GraphQL security schema extensions.

Strawberry ``SchemaExtension`` implementations for security concerns.
This approach integrates cleanly with Strawberry's execution pipeline so
security checks run inside the schema lifecycle rather than in the executor.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from strawberry.extensions import SchemaExtension

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from lexigram.graphql.security.rate_limit import RateLimiter

logger = get_logger(__name__)


class RateLimitExtension(SchemaExtension):
    """Enforce rate limiting on every GraphQL operation.

    This extension delegates the actual limit check to the injected
    :class:`~lexigram.graphql.security.rate_limit.RateLimiter` (resolved
    from the DI container by :class:`~lexigram.graphql.providers.GraphQLProvider`)
    and raises :class:`~lexigram.graphql.exceptions.RateLimitError` when the
    limit is exceeded.

    Register it on the schema builder instead of wiring it into the executor::

        builder.add_extension(
            RateLimitExtension(rate_limiter=rate_limiter, max_requests=60)
        )

    Args:
        rate_limiter: Rate limiter implementation; when ``None`` the extension
            is a no-op (useful for local/test environments).
        max_requests: Request allowance per window.
        window_seconds: Window length in seconds.
    """

    def __init__(
        self,
        *,
        rate_limiter: RateLimiter | None = None,
        max_requests: int = 60,
        window_seconds: int = 60,
    ) -> None:
        self._rate_limiter = rate_limiter
        self._max_requests = max_requests
        self._window_seconds = window_seconds

    async def on_operation(self) -> AsyncGenerator[None, None]:
        """Check the rate limit before the GraphQL operation executes."""
        if self._rate_limiter is not None:
            context = self.execution_context.context

            from lexigram.graphql.exceptions import RateLimitError

            try:
                allowed = await self._rate_limiter.is_allowed(
                    context,
                    max_requests=self._max_requests,
                    window_seconds=self._window_seconds,
                )
                if not allowed:
                    raise RateLimitError("Rate limit exceeded")
            except RateLimitError:
                raise
            except (OSError, RuntimeError, LookupError) as e:
                # Infrastructure errors (Redis down etc.) must not block requests.
                logger.warning("rate_limit_check_error", error=str(e))

        yield


__all__ = ["RateLimitExtension"]
