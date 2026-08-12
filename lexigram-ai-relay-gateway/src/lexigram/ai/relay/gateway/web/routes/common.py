from __future__ import annotations

"""Shared request-resolution and auth/rate-limit machinery for the relay routes."""

from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any, TypeAlias

from starlette.requests import Request
from starlette.responses import Response

from lexigram.ai.relay.gateway.catalog import ModelCatalogService
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.job_passthrough import JobPassthroughService
from lexigram.ai.relay.gateway.logging import RelayRequestLogger
from lexigram.ai.relay.gateway.ratelimit import RelayRateLimiter
from lexigram.ai.relay.gateway.web.shared import (
    _REQUIRE_AUTH_MISCONFIGURED,
    _RequireAuthMisconfigured,
    _status_for,
    auth_guard,
    log_request,
    rate_limit_guard,
)
from lexigram.contracts.ai.relay import (
    RelayAuthVerifierProtocol,
    RelayFormat,
    RelayGatewayProtocol,
    RelayRateLimitCounterProtocol,
    RelayRequestLogStoreProtocol,
)

ResolveGateway: TypeAlias = Callable[[Request], Awaitable[RelayGatewayProtocol]]
"""Resolver of a gateway implementation from a Starlette request."""

ResolveJobPassthrough: TypeAlias = Callable[[Request], Awaitable[JobPassthroughService]]
"""Resolver of a job passthrough service from a Starlette request."""

ResolveModelCatalog: TypeAlias = Callable[[Request], Awaitable[ModelCatalogService]]
"""Resolver of the model catalog service from a Starlette request."""


async def _resolve_verifier(
    request: Request,
) -> RelayAuthVerifierProtocol | _RequireAuthMisconfigured | None:
    """Resolve the verifier when auth is required, else ``None``.

    ``None`` means auth is explicitly off (no config, or
    ``require_auth=False``).  When auth is required but no verifier is
    bound, the ``_RequireAuthMisconfigured`` sentinel is returned so
    ``auth_guard`` fails closed instead of passing through silently.
    """
    container: Any = getattr(request.state, "container", None)
    if container is None:
        return None
    config = await container.resolve_optional(RelayGatewayConfig)
    if config is None or not config.require_auth:
        return None
    verifier = await container.resolve_optional(RelayAuthVerifierProtocol)
    if verifier is None:
        return _REQUIRE_AUTH_MISCONFIGURED
    return verifier


async def _resolve_limiter(request: Request) -> RelayRateLimiter | None:
    """Build the limiter from config when rules are set, else ``None``.

    The counter comes from the container; an unbound counter leaves the
    limiter inert (pass-through), and an empty ``rate_limits`` map
    disables the guard entirely — today's behavior either way.
    """
    container: Any = getattr(request.state, "container", None)
    if container is None:
        return None
    config = await container.resolve_optional(RelayGatewayConfig)
    if config is None or not config.rate_limits:
        return None
    counter = await container.resolve_optional(RelayRateLimitCounterProtocol)
    return RelayRateLimiter(rules=config.rate_limits, counter=counter)


async def _resolve_logger(request: Request) -> RelayRequestLogger | None:
    """Resolve the request-log emitter, or ``None`` when no store is bound."""
    container: Any = getattr(request.state, "container", None)
    if container is None:
        return None
    store = await container.resolve_optional(RelayRequestLogStoreProtocol)
    if store is None:
        return None
    return RelayRequestLogger(store=store)


def _dispatch_latency_ms(started: float) -> int:
    """Round the monotonic dispatch span to whole milliseconds."""
    return round((monotonic() - started) * 1000)


_SOURCE_KIND: dict[RelayFormat, str] = {
    RelayFormat.OPENAI_CHAT: "chat",
    RelayFormat.OPENAI_RESPONSES: "responses",
    RelayFormat.CLAUDE: "messages",
    RelayFormat.GEMINI: "generateContent",
}
"""Wire format to request-log endpoint-kind label."""


async def _log_dispatch(  # noqa: PLR0917 - six positional log fields
    request: Request,
    source: RelayFormat,
    model: str,
    status_code: int,
    error_code: str,
    started: float,
) -> None:
    """Emit the terminal dispatch entry through the resolved logger."""
    logger = await _resolve_logger(request)
    if logger is None:
        return
    log_request(
        request,
        logger,
        kind=_SOURCE_KIND[source],
        status=_status_for(status_code),
        model=model,
        error_code=error_code,
        latency_ms=_dispatch_latency_ms(started),
    )


def _with_auth_guard(
    handler: Callable[..., Awaitable[Response]],
) -> Callable[..., Awaitable[Response]]:
    """Wrap a route handler so auth and rate limiting run first.

    Auth is on by default; pass-through only happens when auth is
    explicitly opted out (``require_auth=False``) or no gateway config
    is present.
    """

    async def guarded(request: Request) -> Response:
        verifier = await _resolve_verifier(request)
        limiter = await _resolve_limiter(request)

        async def inner(req: Request) -> Response:
            blocked = await rate_limit_guard(req, limiter)
            if blocked is not None:
                return blocked
            return await handler(req)

        return await auth_guard(request, verifier, inner)

    return guarded


async def _log_kind_dispatch(  # noqa: PLR0917 - six positional log fields
    request: Request,
    kind: str,
    model: str,
    status_code: int,
    error_code: str,
    started: float,
) -> None:
    """Emit a terminal dispatch entry for passthrough and job routes."""
    logger = await _resolve_logger(request)
    if logger is None:
        return
    log_request(
        request,
        logger,
        kind=kind,
        status=_status_for(status_code),
        model=model,
        error_code=error_code,
        latency_ms=_dispatch_latency_ms(started),
    )
