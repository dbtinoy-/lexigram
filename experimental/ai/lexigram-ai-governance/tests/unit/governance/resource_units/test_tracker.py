"""Tests for ResourceUnitTracker (LXF-001).

RED phase — these fail because the tracker doesn't exist yet.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("lexigram.ai.governance.resource.tracker")


@pytest.fixture
def registry():
    from lexigram.ai.governance.resource.registry import (
        ResourceUnitRegistry,
    )
    from lexigram.contracts.ai.governance.resource_unit import (
        ResourceUnit,
        ResourceWindowKind,
    )

    return ResourceUnitRegistry.from_list(
        [
            ResourceUnit(
                name="render_minutes",
                unit_kind="minutes",
                window=timedelta(hours=1),
                window_kind=ResourceWindowKind.SLIDING,
            ),
            ResourceUnit(
                name="concurrent_episodes",
                unit_kind="count",
                window_kind=ResourceWindowKind.INSTANTANEOUS,
            ),
            ResourceUnit(
                name="daily_calls",
                unit_kind="count",
                window=timedelta(days=1),
                window_kind=ResourceWindowKind.CALENDAR,
            ),
        ]
    )


@pytest.fixture
def persistence():
    return AsyncMock()


@pytest.fixture
def tracker(registry, persistence):
    from lexigram.ai.governance.resource.tracker import (
        ResourceUnitTracker,
    )

    def get_quota(tenant_id: str, unit_name: str) -> float:
        limits = {
            ("t1", "render_minutes"): 1000.0,
            ("t1", "concurrent_episodes"): 5.0,
            ("t1", "daily_calls"): 100.0,
            ("t2", "render_minutes"): 500.0,
        }
        return limits.get((tenant_id, unit_name), 0.0)

    return ResourceUnitTracker(
        registry=registry,
        persistence=persistence,
        get_quota=get_quota,
    )


class TestConstruct:
    def test_constructor_requires_registry_and_persistence(self):
        from lexigram.ai.governance.resource.tracker import (
            ResourceUnitTracker,
        )
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceUnit,
            ResourceWindowKind,
        )
        from lexigram.ai.governance.resource.registry import (
            ResourceUnitRegistry,
        )

        registry = ResourceUnitRegistry()
        persistence = AsyncMock()
        tracker = ResourceUnitTracker(
            registry=registry, persistence=persistence
        )
        assert tracker is not None


class TestConsume:
    @pytest.mark.asyncio
    async def test_consume_sliding_ok(self, tracker, persistence):
        persistence.incr_requests = AsyncMock(return_value=100)
        result = await tracker.consume(
            tenant_id="t1",
            unit_name="render_minutes",
            amount=100,
        )
        assert result.is_ok()
        snap = result.unwrap()
        assert snap.tenant_id == "t1"
        assert snap.unit_name == "render_minutes"
        assert snap.current == 100

    @pytest.mark.asyncio
    async def test_consume_sliding_exhausted(self, tracker, persistence):
        persistence.incr_requests = AsyncMock(return_value=1100)
        result = await tracker.consume(
            tenant_id="t1",
            unit_name="render_minutes",
            amount=1100,
        )
        assert result.is_err()
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceExhaustedError,
        )

        assert isinstance(result.unwrap_err(), ResourceExhaustedError)

    @pytest.mark.asyncio
    async def test_consume_instantaneous_ok(
        self, tracker, persistence
    ):
        persistence.read_gauge = AsyncMock(return_value=2)
        persistence.incr_gauge = AsyncMock(return_value=3)
        result = await tracker.consume(
            tenant_id="t1",
            unit_name="concurrent_episodes",
            amount=1,
        )
        assert result.is_ok()
        snap = result.unwrap()
        assert snap.current == 3

    @pytest.mark.asyncio
    async def test_consume_instantaneous_exhausted(
        self, tracker, persistence
    ):
        persistence.read_gauge = AsyncMock(return_value=6)
        result = await tracker.consume(
            tenant_id="t1",
            unit_name="concurrent_episodes",
            amount=1,
        )
        assert result.is_err()
        persistence.incr_gauge.assert_not_called()

    @pytest.mark.asyncio
    async def test_consume_calendar_ok(self, tracker, persistence):
        persistence.incr_calendar = AsyncMock(return_value=50)
        result = await tracker.consume(
            tenant_id="t1", unit_name="daily_calls", amount=50
        )
        assert result.is_ok()
        snap = result.unwrap()
        assert snap.current == 50

    @pytest.mark.asyncio
    async def test_consume_unknown_unit(self, tracker, persistence):
        result = await tracker.consume(
            tenant_id="t1", unit_name="nonexistent", amount=10
        )
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_consume_no_quota_denies(self, tracker, persistence):
        result = await tracker.consume(
            tenant_id="unknown", unit_name="render_minutes", amount=1
        )
        assert result.is_err()


class TestRelease:
    @pytest.mark.asyncio
    async def test_release_instantaneous(self, tracker, persistence):
        persistence.decr_gauge = AsyncMock()
        await tracker.release(
            tenant_id="t1",
            unit_name="concurrent_episodes",
            amount=1,
        )
        persistence.decr_gauge.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_release_sliding_noop(self, tracker, persistence):
        await tracker.release(
            tenant_id="t1",
            unit_name="render_minutes",
            amount=1,
        )
        # Sliding windows decay naturally — release is a no-op
        persistence.decr_gauge.assert_not_called()

    @pytest.mark.asyncio
    async def test_release_unknown_unit(self, tracker, persistence):
        await tracker.release(
            tenant_id="t1", unit_name="nonexistent", amount=1
        )
        # Should not raise
        persistence.decr_gauge.assert_not_called()


class TestUsage:
    @pytest.mark.asyncio
    async def test_usage_sliding(self, tracker, persistence):
        persistence.incr_requests = AsyncMock(return_value=251)
        snap = await tracker.usage(
            tenant_id="t1", unit_name="render_minutes"
        )
        assert snap.tenant_id == "t1"
        assert snap.unit_name == "render_minutes"
        assert snap.current == 250.0

    @pytest.mark.asyncio
    async def test_usage_instantaneous(self, tracker, persistence):
        persistence.read_gauge = AsyncMock(return_value=3)
        snap = await tracker.usage(
            tenant_id="t1", unit_name="concurrent_episodes"
        )
        assert snap.current == 3

    @pytest.mark.asyncio
    async def test_usage_calendar(self, tracker, persistence):
        persistence.get_calendar = AsyncMock(return_value=75.0)
        snap = await tracker.usage(
            tenant_id="t1", unit_name="daily_calls"
        )
        assert snap.current == 75.0
