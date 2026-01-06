"""Tests for lexigram.primitives — TransformPipe transformation chain."""

from __future__ import annotations

import pytest

from lexigram.workflow.core.pipe import TransformPipe


class TestTransformPipe:
    """Tests for TransformPipe."""

    @pytest.mark.asyncio
    async def test_basic_pipe(self) -> None:
        pipe: TransformPipe[int] = TransformPipe()

        async def add_one(x: int) -> int:
            return x + 1

        async def double(x: int) -> int:
            return x * 2

        result = await pipe.pipe(add_one).pipe(double).execute(5)
        assert result == 12

    @pytest.mark.asyncio
    async def test_empty_pipe(self) -> None:
        pipe: TransformPipe[str] = TransformPipe()
        result = await pipe.execute("hello")
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_immutability(self) -> None:
        pipe: TransformPipe[int] = TransformPipe()

        async def add_one(x: int) -> int:
            return x + 1

        p2 = pipe.pipe(add_one)
        assert await pipe.execute(5) == 5
        assert await p2.execute(5) == 6

    @pytest.mark.asyncio
    async def test_sync_step(self) -> None:
        pipe: TransformPipe[str] = TransformPipe()

        def upper(x: str) -> str:
            return x.upper()

        result = await pipe.pipe(upper).execute("hello")
        assert result == "HELLO"

    def test_len(self) -> None:
        p = TransformPipe().pipe(lambda x: x).pipe(lambda x: x)
        assert len(p) == 2

    def test_repr(self) -> None:
        p = TransformPipe().pipe(lambda x: x)
        assert repr(p) == "TransformPipe(steps=1)"
