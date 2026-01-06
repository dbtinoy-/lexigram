"""Tests for RunnableLambda."""
from __future__ import annotations

import pytest

from lexigram.result import Err, Ok, Result


class TestRunnableLambda:
    """Tests for RunnableLambda."""

    def test_sync_lambda_invoke(self) -> None:
        """Sync lambda should work with invoke."""
        from lexigram.ai.llm.runnable.lambda_ import RunnableLambda

        runnable = RunnableLambda(lambda x: x.upper())
        result = runnable.invoke("hello")
        assert result == "HELLO"

    @pytest.mark.asyncio
    async def test_sync_lambda_ainvoke(self) -> None:
        """Sync lambda should work with ainvoke."""
        from lexigram.ai.llm.runnable.lambda_ import RunnableLambda

        runnable = RunnableLambda(lambda x: x.upper())
        result = await runnable.ainvoke("hello")
        assert result == "HELLO"

    @pytest.mark.asyncio
    async def test_async_lambda_ainvoke(self) -> None:
        """Async lambda should work with ainvoke."""
        from lexigram.ai.llm.runnable.lambda_ import RunnableLambda

        async def async_upper(x: str) -> str:
            return x.upper()

        runnable = RunnableLambda(async_upper)
        result = await runnable.ainvoke("hello")
        assert result == "HELLO"

    def test_sync_lambda_ainvoke_works(self) -> None:
        """Sync lambda should work with ainvoke (just calls the func)."""
        from lexigram.ai.llm.runnable.lambda_ import RunnableLambda

        runnable = RunnableLambda(lambda x: x.upper())
        result = runnable.ainvoke("hello")
        import asyncio
        ret = asyncio.run(result)
        assert ret == "HELLO"

    def test_lambda_catches_exception(self) -> None:
        """Lambda should catch exceptions and return Err."""
        from lexigram.ai.llm.runnable.lambda_ import RunnableLambda

        runnable = RunnableLambda(lambda x: x.upper())
        result = runnable.invoke(123)
        assert isinstance(result, Err)
