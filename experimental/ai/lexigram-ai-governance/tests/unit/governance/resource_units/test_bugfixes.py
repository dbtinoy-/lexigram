"""Regression tests for three known bugs — written before fixes (RED phase).

Each test verifies the bug assertion BEFORE the fix (should fail on current code).
"""

from __future__ import annotations

import typing
from datetime import timedelta

import pytest

from lexigram.ai.governance.persistence import (
    DatabaseGovernancePersistence,
    GovernancePersistence,
    InMemoryGovernancePersistence,
    RedisGovernancePersistence,
)


class TestBug1IncrGaugeDeltaType:
    """Bug 1: incr_gauge delta: int should be delta: float (decr_gauge passes -amount)."""

    def test_protocol_incr_gauge_delta_is_float(self):
        """Protocol's incr_gauge must declare delta: float (currently int)."""
        hints = typing.get_type_hints(GovernancePersistence.incr_gauge)
        assert hints["delta"] is float

    def test_in_memory_incr_gauge_delta_is_float(self):
        hints = typing.get_type_hints(InMemoryGovernancePersistence.incr_gauge)
        assert hints["delta"] is float

    def test_redis_incr_gauge_delta_is_float(self):
        hints = typing.get_type_hints(RedisGovernancePersistence.incr_gauge)
        assert hints["delta"] is float

    def test_database_incr_gauge_delta_is_float(self):
        hints = typing.get_type_hints(DatabaseGovernancePersistence.incr_gauge)
        assert hints["delta"] is float


class TestBug2InstantaneousGaugeLeak:
    """Bug 2: INSTANTANEOUS consume increments gauge BEFORE quota check — gauge leaks."""

    @pytest.fixture
    def tracker(self):
        from lexigram.ai.governance.resource.registry import ResourceUnitRegistry
        from lexigram.ai.governance.resource.tracker import ResourceUnitTracker
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceUnit,
            ResourceWindowKind,
        )

        registry = ResourceUnitRegistry.from_list([
            ResourceUnit(
                name="concurrent",
                unit_kind="count",
                window_kind=ResourceWindowKind.INSTANTANEOUS,
            ),
        ])
        persistence = InMemoryGovernancePersistence()

        def get_quota(tenant_id: str, unit_name: str) -> float:
            return 5.0 if tenant_id == "t1" else 0.0

        return ResourceUnitTracker(
            registry=registry,
            persistence=persistence,
            get_quota=get_quota,
        )

    @pytest.mark.asyncio
    async def test_quota_exceeded_does_not_leak_gauge(self, tracker):
        """When quota is exceeded, the gauge must not have been incremented."""
        result = await tracker.consume("t1", "concurrent", 5.0)
        assert result.is_ok()

        snap_before = await tracker.usage("t1", "concurrent")
        assert snap_before.current == 5.0

        result_exceeded = await tracker.consume("t1", "concurrent", 1.0)
        assert result_exceeded.is_err()

        snap_after = await tracker.usage("t1", "concurrent")
        assert snap_after.current == 5.0


class TestBug3SlidingUsagePathMismatch:
    """Bug 3: SLIDING usage() reads from get_spend but writes via incr_requests."""

    @pytest.fixture
    def tracker(self):
        from lexigram.ai.governance.resource.registry import ResourceUnitRegistry
        from lexigram.ai.governance.resource.tracker import ResourceUnitTracker
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceUnit,
            ResourceWindowKind,
        )

        registry = ResourceUnitRegistry.from_list([
            ResourceUnit(
                name="render_minutes",
                unit_kind="minutes",
                window=timedelta(hours=1),
                window_kind=ResourceWindowKind.SLIDING,
            ),
        ])
        persistence = InMemoryGovernancePersistence()

        def get_quota(tenant_id: str, unit_name: str) -> float:
            return 1000.0 if tenant_id == "t1" else 0.0

        return ResourceUnitTracker(
            registry=registry,
            persistence=persistence,
            get_quota=get_quota,
        )

    @pytest.mark.asyncio
    async def test_usage_returns_same_as_consume_snapshot(self, tracker):
        """usage() returns the same request count as consume — not 0 from empty spend path."""
        result = await tracker.consume("t1", "render_minutes", 50.0)
        assert result.is_ok()
        assert result.unwrap().current == 1.0

        snap = await tracker.usage("t1", "render_minutes")
        assert snap.current == 1.0
