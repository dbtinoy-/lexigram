"""Redis fixed-window rate limit counter mirroring new-api's Lua semantics.

The single Lua script makes increment, expiry, and the limit decision
atomic while retaining the simple fixed-window behavior: traffic at a
window boundary can burst up to twice the configured limit.  Sliding
windows are intentionally not supported, matching new-api.
"""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING, cast

from lexigram.contracts.ai.relay import (
    RelayRateLimitDecision,
)

if TYPE_CHECKING:
    import redis.asyncio as aioredis

__all__ = ["RedisRateLimitCounter"]

# Mirrors new-api middleware/rate-limit.go's redisFixedWindowScript exactly.
_FIXED_WINDOW_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[2])
end
local ttl = redis.call('TTL', KEYS[1])
if ttl < 0 then
  redis.call('EXPIRE', KEYS[1], ARGV[2])
  ttl = redis.call('TTL', KEYS[1])
end
if count > tonumber(ARGV[1]) then
  return {0, count, ttl}
end
return {1, count, ttl}
"""


class RedisRateLimitCounter:
    """Fixed-window counter backed by an ``redis.asyncio.Redis`` client.

    Uses the exact new-api Lua script via ``EVAL`` so increment, expiry,
    and the limit decision are atomic on the server.
    """

    def __init__(self, client: aioredis.Redis) -> None:
        """Initialise with the Redis client.

        Args:
            client: An ``redis.asyncio.Redis`` instance (injected by the
                caller, typically resolved from the container).
        """
        self._client = client

    async def take(
        self, key: str, limit: int, window_seconds: int
    ) -> RelayRateLimitDecision:
        """Atomically increment the counter for *key* within its window.

                Args:
                    key: The rate-limit bucket key.
                    limit: Maximum allowed requests per window.
                    window_seconds: Window length in seconds.

        Returns:
                    The decision with the post-increment count and remaining
                    window TTL.
        """
        result = cast(
            "Awaitable[list[int]]",
            self._client.eval(
                _FIXED_WINDOW_SCRIPT, 1, key, limit, window_seconds
            ),
        )
        values = await result
        allowed, count, ttl = values
        return RelayRateLimitDecision(
            allowed=allowed == 1, count=int(count), ttl_seconds=int(ttl)
        )
