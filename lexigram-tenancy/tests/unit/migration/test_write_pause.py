"""Unit tests for WritePauseRegistry."""

from __future__ import annotations

import pytest

from lexigram.tenancy.migration.write_pause import WritePauseRegistry


class TestWritePauseRegistry:
    """Suite for WritePauseRegistry with no cache backend."""

    @pytest.fixture
    def registry(self) -> WritePauseRegistry:
        return WritePauseRegistry()

    async def test_is_paused_returns_false_by_default(
        self, registry: WritePauseRegistry
    ) -> None:
        assert await registry.is_paused("tenant-abc") is False

    async def test_pause_then_is_paused(
        self, registry: WritePauseRegistry
    ) -> None:
        await registry.pause("tenant-abc")
        assert await registry.is_paused("tenant-abc") is True

    async def test_pause_reason(
        self, registry: WritePauseRegistry
    ) -> None:
        await registry.pause("tenant-abc", reason="scheduled migration")
        assert await registry.pause_reason("tenant-abc") == "scheduled migration"

    async def test_resume_clears_pause(
        self, registry: WritePauseRegistry
    ) -> None:
        await registry.pause("tenant-abc")
        await registry.resume("tenant-abc")
        assert await registry.is_paused("tenant-abc") is False

    async def test_resume_nonexistent_is_noop(
        self, registry: WritePauseRegistry
    ) -> None:
        await registry.resume("nonexistent")
        assert await registry.is_paused("nonexistent") is False

    async def test_pause_reason_returns_none_when_not_paused(
        self, registry: WritePauseRegistry
    ) -> None:
        assert await registry.pause_reason("tenant-abc") is None

    async def test_multiple_tenants_independent(
        self, registry: WritePauseRegistry
    ) -> None:
        await registry.pause("tenant-a")
        await registry.pause("tenant-b")
        assert await registry.is_paused("tenant-a") is True
        assert await registry.is_paused("tenant-b") is True
        await registry.resume("tenant-a")
        assert await registry.is_paused("tenant-a") is False
        assert await registry.is_paused("tenant-b") is True

    async def test_default_reason(
        self, registry: WritePauseRegistry
    ) -> None:
        await registry.pause("tenant-abc")
        assert await registry.pause_reason("tenant-abc") == "migration"
