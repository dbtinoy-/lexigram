"""Tests for data/lazy.py utilities."""

from __future__ import annotations

import pytest


class TestLazyField:
    """Tests for LazyField (data/lazy.py)."""

    @pytest.mark.asyncio
    async def test_get_loads_on_first_call(self) -> None:
        from lexigram.admin.data.lazy import LazyField

        call_count = 0

        async def loader() -> str:
            nonlocal call_count
            call_count += 1
            return "loaded_value"

        field = LazyField(loader)
        assert not field.is_loaded
        value = await field.get()
        assert value == "loaded_value"
        assert field.is_loaded
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_get_caches_result(self) -> None:
        from lexigram.admin.data.lazy import LazyField

        call_count = 0

        async def loader() -> int:
            nonlocal call_count
            call_count += 1
            return 42

        field = LazyField(loader)
        await field.get()
        await field.get()
        await field.get()
        assert call_count == 1  # Only loaded once

    @pytest.mark.asyncio
    async def test_is_loaded_false_before_get(self) -> None:
        from lexigram.admin.data.lazy import LazyField

        async def noop() -> None:
            return None

        lazy_field: LazyField[None] = LazyField(noop)
        assert not lazy_field.is_loaded

    @pytest.mark.asyncio
    async def test_is_loaded_true_after_get(self) -> None:
        from lexigram.admin.data.lazy import LazyField

        async def loader() -> dict:
            return {"key": "val"}

        field = LazyField(loader)
        await field.get()
        assert field.is_loaded


class TestDeferredField:
    """Tests for DeferredField (data/lazy.py)."""

    def test_stores_original_type(self) -> None:
        from lexigram.admin.data.lazy import DeferredField

        df = DeferredField(str)
        assert df.original_type is str

    def test_stores_complex_type(self) -> None:
        from lexigram.admin.data.lazy import DeferredField

        df = DeferredField(list[int])
        assert df.original_type == list[int]
