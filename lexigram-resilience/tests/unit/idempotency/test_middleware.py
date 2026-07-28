"""Tests for IdempotencyMiddleware."""

from __future__ import annotations

import pytest

from lexigram.resilience.config import IdempotencyConfig
from lexigram.resilience.idempotency.middleware import IdempotencyMiddleware
from lexigram.resilience.idempotency.store import InMemoryIdempotencyStore


def _make_middleware(
    ttl: int = 300, max_key_length: int = 255
) -> tuple[IdempotencyMiddleware, InMemoryIdempotencyStore]:
    store = InMemoryIdempotencyStore()
    config = IdempotencyConfig(ttl=ttl, max_key_length=max_key_length)
    return IdempotencyMiddleware(store=store, config=config), store


class TestIdempotencyMiddlewarePassThrough:
    """Tests for requests without an idempotency key (pass-through behaviour)."""

    @pytest.mark.asyncio
    async def test_no_header_passes_through(self) -> None:
        """Handler is called directly when no Idempotency-Key header is present."""
        middleware, _ = _make_middleware()
        call_count = 0

        async def handler() -> dict:
            nonlocal call_count
            call_count += 1
            return {"created": True}

        result = await middleware.process({}, handler)

        assert result == {"created": True}
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_empty_header_passes_through(self) -> None:
        """An empty Idempotency-Key header value is treated as absent."""
        middleware, _ = _make_middleware()
        call_count = 0

        async def handler() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await middleware.process({"idempotency-key": ""}, handler)

        assert result == "ok"
        assert call_count == 1


class TestIdempotencyMiddlewareCacheMiss:
    """Tests for first-time requests — cache miss path."""

    @pytest.mark.asyncio
    async def test_cache_miss_calls_handler(self) -> None:
        """Handler is invoked and result is stored on a cache miss."""
        middleware, _ = _make_middleware()
        call_count = 0

        async def handler() -> dict:
            nonlocal call_count
            call_count += 1
            return {"id": "order-1"}

        result = await middleware.process({"idempotency-key": "req-abc"}, handler)

        assert result == {"id": "order-1"}
        assert call_count == 1


class TestIdempotencyMiddlewareCacheHit:
    """Tests for duplicate requests — cache hit / replay path."""

    @pytest.mark.asyncio
    async def test_second_request_replays_result(self) -> None:
        """Duplicate key returns cached result without invoking the handler again."""
        middleware, _ = _make_middleware()
        call_count = 0

        async def handler() -> dict:
            nonlocal call_count
            call_count += 1
            return {"id": "order-1"}

        # First request executes
        first = await middleware.process({"idempotency-key": "req-xyz"}, handler)
        # Second request with same key must replay without calling handler
        second = await middleware.process({"idempotency-key": "req-xyz"}, handler)

        assert first == second
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_different_keys_execute_independently(self) -> None:
        """Different idempotency keys each trigger independent handler execution."""
        middleware, _ = _make_middleware()
        call_count = 0

        async def handler() -> dict:
            nonlocal call_count
            call_count += 1
            return {"call": call_count}

        await middleware.process({"idempotency-key": "key-1"}, handler)
        await middleware.process({"idempotency-key": "key-2"}, handler)

        assert call_count == 2


class TestIdempotencyMiddlewareKeyLength:
    """Tests for the max_key_length guard."""

    @pytest.mark.asyncio
    async def test_key_exceeding_max_length_is_ignored(self) -> None:
        """Keys longer than max_key_length behave as pass-through (no key)."""
        middleware, _ = _make_middleware(max_key_length=10)
        call_count = 0

        async def handler() -> str:
            nonlocal call_count
            call_count += 1
            return "result"

        # Two requests with the same oversized key should each execute the handler
        await middleware.process({"idempotency-key": "x" * 20}, handler)
        await middleware.process({"idempotency-key": "x" * 20}, handler)

        assert call_count == 2
