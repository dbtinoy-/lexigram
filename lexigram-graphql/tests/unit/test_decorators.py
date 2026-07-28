from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.graphql.decorators import log_resolver, retry_resolver


class TestRetryResolver:
    @pytest.mark.asyncio
    async def test_success_no_retry(self) -> None:
        fn = AsyncMock(return_value="ok")

        @retry_resolver(max_retries=3, delay=0.01)
        async def decorated() -> str:
            return await fn()

        result = await decorated()
        assert result == "ok"
        fn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retry_on_exception_then_succeed(self) -> None:
        fn = AsyncMock(side_effect=[ValueError("first"), ValueError("second"), "ok"])

        @retry_resolver(max_retries=3, delay=0.01, exceptions=(ValueError,))
        async def decorated() -> str:
            return await fn()

        result = await decorated()
        assert result == "ok"
        assert fn.await_count == 3

    @pytest.mark.asyncio
    async def test_exhaust_retries(self) -> None:
        fn = AsyncMock(side_effect=ValueError("always fails"))

        @retry_resolver(max_retries=2, delay=0.01, exceptions=(ValueError,))
        async def decorated() -> str:
            return await fn()

        with pytest.raises(ValueError, match="always fails"):
            await decorated()
        assert fn.await_count == 2

    @pytest.mark.asyncio
    async def test_non_matching_exception_not_retried(self) -> None:
        fn = AsyncMock(side_effect=TypeError("wrong type"))

        @retry_resolver(max_retries=2, delay=0.01, exceptions=(ValueError,))
        async def decorated() -> str:
            return await fn()

        with pytest.raises(TypeError, match="wrong type"):
            await decorated()
        fn.assert_awaited_once()


class TestLogResolver:
    @pytest.mark.asyncio
    async def test_logs_entry_exit(self) -> None:
        fn = AsyncMock(return_value="result")

        @log_resolver
        async def decorated() -> str:
            return await fn()

        result = await decorated()
        assert result == "result"

    @pytest.mark.asyncio
    async def test_logs_and_reraises_error(self) -> None:
        fn = AsyncMock(side_effect=ValueError("oops"))

        @log_resolver
        async def decorated() -> str:
            return await fn()

        with pytest.raises(ValueError, match="oops"):
            await decorated()
