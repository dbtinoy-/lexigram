"""Tests for SystemSetting model and data/lazy.py utilities."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest


class TestSystemSetting:
    """Tests for SystemSetting dataclass (models/setting.py)."""

    def test_required_fields(self) -> None:
        from lexigram.admin.models.setting import SystemSetting

        s = SystemSetting(key="site.title", value="My Admin")
        assert s.key == "site.title"
        assert s.value == "My Admin"

    def test_defaults(self) -> None:
        from lexigram.admin.models.setting import SystemSetting

        s = SystemSetting(key="k", value="v")
        assert s.scope == "global"
        assert s.scope_id == "system"
        assert s.type == "string"
        assert s.is_sensitive is False
        assert s.updated_at is None
        assert s.updated_by is None
        assert s.id is None

    def test_custom_fields(self) -> None:
        from lexigram.admin.models.setting import SystemSetting

        now = datetime.now(UTC)
        s = SystemSetting(
            key="db.url",
            value="postgres://...",
            scope="tenant",
            scope_id="tenant-42",
            type="string",
            is_sensitive=True,
            updated_at=now,
            updated_by="admin",
            id=7,
        )
        assert s.scope == "tenant"
        assert s.scope_id == "tenant-42"
        assert s.is_sensitive is True
        assert s.updated_by == "admin"
        assert s.id == 7
        assert s.updated_at == now


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
