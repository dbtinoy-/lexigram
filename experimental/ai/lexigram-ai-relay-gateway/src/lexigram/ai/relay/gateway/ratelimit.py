"""Fixed-window rate limiting for the relay gateway.

``RelayRateLimiter`` applies per-token and per-model rules from the
gateway config against a swappable fixed-window counter backend.  The
counter contract lives in contracts (``RelayRateLimitCounterProtocol``);
the gateway ships two backends: an in-memory counter for tests/dev and
a Redis fixed-window counter mirroring new-api's Lua semantics (in
``ratelimit_redis``).  Fixed-window semantics intentionally allow a 2x
burst at window boundaries, matching new-api; sliding windows are out of
scope.
"""

from __future__ import annotations

from collections.abc import Mapping

from lexigram.contracts.ai.relay import (
    RelayAuthIdentity,
    RelayRateLimitCounterProtocol,
    RelayRateLimitDecision,
)
from lexigram.primitives import clock

__all__ = ["InMemoryRateLimitCounter", "RelayRateLimiter"]


class InMemoryRateLimitCounter:
    """Process-local fixed-window counter.

    Keeps one ``(window_start, count)`` slot per key and resets the slot
    whenever the elapsed monotonic time exceeds the window.  Async only
    to satisfy the counter protocol; no I/O happens.
    """

    def __init__(self) -> None:
        """Initialise an empty window table."""
        self._windows: dict[str, tuple[float, int]] = {}

    async def take(
        self, key: str, limit: int, window_seconds: int
    ) -> RelayRateLimitDecision:
        """Increment the counter for *key* within its window.

        Args:
            key: The rate-limit bucket key.
            limit: Maximum allowed requests per window.
            window_seconds: Window length in seconds.

        Returns:
            The decision with the post-increment count and remaining
            window TTL.
        """
        now = clock.monotonic()
        start, count = self._windows.get(key, (now, 0))
        if now - start >= window_seconds:
            start, count = now, 0
        count += 1
        self._windows[key] = (start, count)
        ttl = max(0, int(window_seconds - (now - start)))
        return RelayRateLimitDecision(
            allowed=count <= limit, count=count, ttl_seconds=ttl
        )


class RelayRateLimiter:
    """Apply gateway rate-limit rules against a counter backend.

    Rules map a model name (or ``"*"`` for the token-wide rule) to a
    ``{"max": int, "window_seconds": int}`` budget.  Token-wide keys
    are ``relay:rl:{token_id}`` and model-scoped keys are
    ``relay:rl:{token_id}:{model}``.  When no rule applies or no counter
    is bound, ``check`` returns ``None`` (pass-through).
    """

    def __init__(
        self,
        *,
        rules: Mapping[str, Mapping[str, int]],
        counter: RelayRateLimitCounterProtocol | None = None,
    ) -> None:
        """Initialise the limiter with its rules and counter.

        Args:
            rules: Model name (or ``"*"``) to budget mapping.
            counter: The fixed-window counter backend; ``None`` keeps the
                limiter inert (pass-through).
        """
        self._rules: dict[str, tuple[int, int]] = {
            model: (budget["max"], budget["window_seconds"])
            for model, budget in rules.items()
        }
        self._counter = counter

    async def check(
        self, identity: RelayAuthIdentity, model: str
    ) -> RelayRateLimitDecision | None:
        """Take one request against the rule matching *identity* and *model*.

        Args:
            identity: The authenticated relay caller.
            model: The requested model name.

        Returns:
            The decision when a rule applies and a counter is bound;
            ``None`` otherwise (pass-through).
        """
        if self._counter is None:
            return None
        limit_window = self._rules.get(model) or self._rules.get("*")
        if limit_window is None:
            return None
        limit, window_seconds = limit_window
        if model in self._rules:
            key = f"relay:rl:{identity.token_id}:{model}"
        else:
            key = f"relay:rl:{identity.token_id}"
        return await self._counter.take(key, limit, window_seconds)
