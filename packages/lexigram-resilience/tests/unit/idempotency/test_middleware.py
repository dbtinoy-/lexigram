"""Tests for IdempotencyMiddleware."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_mock import MockerFixture

from lexigram.contracts.exceptions.idempotency import IdempotencyError, IdempotencyStoreError
from lexigram.resilience.config import IdempotencyConfig
from lexigram.resilience.idempotency import middleware as middleware_module
from lexigram.resilience.idempotency.middleware import IdempotencyMiddleware
from lexigram.resilience.idempotency.store import InMemoryIdempotencyStore
from lexigram.result import Err, Ok
from lexigram.testing import FakeLogger


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


class _FailOpenStore:
    """Minimal IdempotencyStoreProtocol fake whose get() is scriptable.

    Lets tests drive the middleware through every read-path failure shape:
    a raised exception, a raised IdempotencyStoreError, an Err result, or
    an Ok result.
    """

    def __init__(
        self, get_result: Any, get_exception: Exception | None = None
    ) -> None:
        self._get_result = get_result
        self._get_exception = get_exception

    async def get(self, key: str) -> Any:
        """Return the scripted result or raise the scripted exception."""
        if self._get_exception is not None:
            raise self._get_exception
        return self._get_result

    async def get_record(self, key: str) -> Any:
        return None

    async def set(self, key: str, value: Any, ttl: float | None = None) -> Any:
        return None

    async def delete(self, key: str) -> Any:
        return None

    async def acquire(self, key: str, ttl: int) -> Any:
        return True


class TestIdempotencyMiddlewareFailOpen:
    """Store failures on read degrade to pass-through instead of crashing."""

    @staticmethod
    def _middleware_with_store(store: _FailOpenStore) -> IdempotencyMiddleware:
        config = IdempotencyConfig(ttl=300, max_key_length=255)
        return IdempotencyMiddleware(store=store, config=config)

    @pytest.mark.asyncio
    async def test_store_raise_fails_open(
        self, mocker: MockerFixture
    ) -> None:
        """A raised store exception degrades to handler pass-through."""
        logger = FakeLogger()
        mocker.patch.object(middleware_module, "logger", logger)
        middleware = self._middleware_with_store(
            _FailOpenStore(None, get_exception=RuntimeError("redis down"))
        )
        call_count = 0

        async def handler() -> dict:
            nonlocal call_count
            call_count += 1
            return {"created": True}

        result = await middleware.process({"idempotency-key": "req-raise"}, handler)

        assert result == {"created": True}
        assert call_count == 1
        logger.assert_logged("warning", "Idempotency store unavailable on read")

    @pytest.mark.asyncio
    async def test_store_err_result_fails_open(
        self, mocker: MockerFixture
    ) -> None:
        """An Err-shaped get() result fails open instead of raising UnwrapError."""
        logger = FakeLogger()
        mocker.patch.object(middleware_module, "logger", logger)
        middleware = self._middleware_with_store(
            _FailOpenStore(get_result=Err(IdempotencyError("backend unavailable")))
        )
        call_count = 0

        async def handler() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await middleware.process({"idempotency-key": "req-err"}, handler)

        assert result == "ok"
        assert call_count == 1
        logger.assert_logged("warning", "Idempotency store unavailable on read")

    @pytest.mark.asyncio
    async def test_store_raises_idempotency_store_error_fails_open(
        self, mocker: MockerFixture
    ) -> None:
        """IdempotencyStoreError raised by the store fails open (Redis store path)."""
        logger = FakeLogger()
        mocker.patch.object(middleware_module, "logger", logger)
        middleware = self._middleware_with_store(
            _FailOpenStore(
                get_result=None,
                get_exception=IdempotencyStoreError("cache backend down"),
            )
        )
        call_count = 0

        async def handler() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await middleware.process(
            {"idempotency-key": "req-store-err"}, handler
        )

        assert result == "ok"
        assert call_count == 1
        logger.assert_logged("warning", "Idempotency store unavailable on read")

    @pytest.mark.asyncio
    async def test_store_ok_result_replays(self) -> None:
        """An Ok-shaped get() result replays without invoking the handler."""
        middleware = self._middleware_with_store(
            _FailOpenStore(get_result=Ok("stored-payload"))
        )
        call_count = 0

        async def handler() -> str:
            nonlocal call_count
            call_count += 1
            return "fresh"

        result = await middleware.process({"idempotency-key": "req-ok"}, handler)

        assert result == "stored-payload"
        assert call_count == 0
