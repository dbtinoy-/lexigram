"""Tests for the Redis fixed-window counter (new-api Lua semantics)."""

from __future__ import annotations

from lexigram.ai.relay.gateway.ratelimit_redis import RedisRateLimitCounter
from lexigram.contracts.ai.relay import RelayRateLimitCounterProtocol


class FakeRedis:
    """Recorded ``eval`` fake shaped like ``redis.asyncio.Redis``."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, int, tuple[object, ...]]] = []
        self._reply: list[int | bytes] = [1, 1, 300]

    def set_reply(self, reply: list[int | bytes]) -> None:
        self._reply = reply

    async def eval(
        self, script: str, numkeys: int, *keys_and_args: object
    ) -> list[int | bytes]:
        self.calls.append((script, numkeys, keys_and_args))
        return self._reply


async def test_take_maps_allowed_reply() -> None:
    redis = FakeRedis()
    counter = RedisRateLimitCounter(client=redis)
    decision = await counter.take("relay:rl:t1", limit=30, window_seconds=300)
    assert decision.allowed is True
    assert decision.count == 1
    assert decision.ttl_seconds == 300


async def test_take_maps_denied_reply() -> None:
    redis = FakeRedis()
    redis.set_reply([0, 31, 10])
    counter = RedisRateLimitCounter(client=redis)
    decision = await counter.take("relay:rl:t1", limit=30, window_seconds=300)
    assert decision.allowed is False
    assert decision.count == 31
    assert decision.ttl_seconds == 10


async def test_eval_records_exact_lua_script() -> None:
    redis = FakeRedis()
    counter = RedisRateLimitCounter(client=redis)
    await counter.take("relay:rl:t1", limit=30, window_seconds=300)
    script, numkeys, args = redis.calls[0]
    assert numkeys == 1
    assert args == ("relay:rl:t1", 30, 300)
    assert "redis.call('INCR', KEYS[1])" in script
    assert "redis.call('EXPIRE', KEYS[1], ARGV[2])" in script
    assert "count > tonumber(ARGV[1])" in script
    assert "return {0, count, ttl}" in script
    assert "return {1, count, ttl}" in script


async def test_protocol_compliance() -> None:
    counter = RedisRateLimitCounter(client=FakeRedis())
    assert isinstance(counter, RelayRateLimitCounterProtocol)
