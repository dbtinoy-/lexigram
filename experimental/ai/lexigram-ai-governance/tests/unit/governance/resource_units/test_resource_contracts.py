"""Tests for resource unit contracts types (LXF-001).

RED phase — these tests fail because the production code doesn't exist yet.
"""

from __future__ import annotations

import pickle
from datetime import timedelta

import pytest

pytest.importorskip("lexigram.contracts.ai.governance.resource_unit")


class TestResourceUnit:
    def test_construct_defaults(self):
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceUnit,
            ResourceWindowKind,
        )

        unit = ResourceUnit(name="render_minutes", unit_kind="minutes")
        assert unit.name == "render_minutes"
        assert unit.unit_kind == "minutes"
        assert unit.window is None
        assert unit.window_kind == ResourceWindowKind.SLIDING

    def test_construct_with_window(self):
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceUnit,
            ResourceWindowKind,
        )

        unit = ResourceUnit(
            name="concurrent_episodes",
            unit_kind="count",
            window=timedelta(hours=1),
            window_kind=ResourceWindowKind.INSTANTANEOUS,
        )
        assert unit.name == "concurrent_episodes"
        assert unit.window == timedelta(hours=1)
        assert unit.window_kind == ResourceWindowKind.INSTANTANEOUS

    def test_immutable(self):
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceUnit,
        )

        unit = ResourceUnit(name="test", unit_kind="count")
        with pytest.raises(AttributeError):
            unit.name = "other"

    def test_pickle_roundtrip(self):
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceUnit,
        )

        orig = ResourceUnit(
            name="test", unit_kind="count", window=timedelta(minutes=5)
        )
        data = pickle.dumps(orig)
        restored = pickle.loads(data)
        assert restored == orig


class TestResourceQuota:
    def test_construct(self):
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceQuota,
            ResourceUnit,
        )

        unit = ResourceUnit(name="render_minutes", unit_kind="minutes")
        quota = ResourceQuota(
            tenant_id="tenant-1",
            unit=unit,
            limit=1000.0,
            soft_threshold_pct=0.8,
        )
        assert quota.tenant_id == "tenant-1"
        assert quota.unit is unit
        assert quota.limit == 1000.0
        assert quota.soft_threshold_pct == 0.8

    def test_immutable(self):
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceQuota,
            ResourceUnit,
        )

        unit = ResourceUnit(name="u1", unit_kind="count")
        quota = ResourceQuota(tenant_id="t1", unit=unit, limit=500.0)
        with pytest.raises(AttributeError):
            quota.limit = 999.0


class TestResourceUsageSnapshot:
    def test_construct(self):
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceUsageSnapshot,
        )

        snap = ResourceUsageSnapshot(
            tenant_id="t1",
            unit_name="render_minutes",
            current=450.0,
            limit=1000.0,
        )
        assert snap.tenant_id == "t1"
        assert snap.unit_name == "render_minutes"
        assert snap.current == 450.0
        assert snap.limit == 1000.0
        assert snap.window_resets_at is None

    def test_immutable(self):
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceUsageSnapshot,
        )

        snap = ResourceUsageSnapshot(
            tenant_id="t1", unit_name="u1", current=100.0, limit=500.0
        )
        with pytest.raises(AttributeError):
            snap.current = 200.0


class TestResourceUsageResult:
    def test_enum_members(self):
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceUsageResult,
        )

        assert ResourceUsageResult.APPROVED.value == "approved"
        assert (
            ResourceUsageResult.SOFT_THRESHOLD_BREACH.value
            == "soft_threshold_breach"
        )
        assert ResourceUsageResult.EXHAUSTED.value == "exhausted"


class TestResourceWindowKind:
    def test_enum_members(self):
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceWindowKind,
        )

        assert ResourceWindowKind.SLIDING.value == "sliding"
        assert ResourceWindowKind.CALENDAR.value == "calendar"
        assert ResourceWindowKind.INSTANTANEOUS.value == "instantaneous"


class TestResourceExhaustedError:
    def test_is_governance_error(self):
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceExhaustedError,
        )
        from lexigram.contracts.ai.governance import GovernanceError

        exc = ResourceExhaustedError(
            tenant_id="t1",
            unit_name="render_minutes",
            limit=1000.0,
            current=1000.0,
        )
        assert isinstance(exc, GovernanceError)
        assert exc.tenant_id == "t1"
        assert exc.unit_name == "render_minutes"
        assert exc.limit == 1000.0
        assert exc.current == 1000.0
        assert str(exc)

    def test_raised_and_caught(self):
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceExhaustedError,
        )

        with pytest.raises(ResourceExhaustedError) as exc_info:
            raise ResourceExhaustedError(
                tenant_id="t1",
                unit_name="u1",
                limit=500.0,
                current=500.0,
            )
        assert exc_info.value.tenant_id == "t1"

    def test_default_code(self):
        from lexigram.contracts.ai.governance.resource_unit import (
            ResourceExhaustedError,
        )

        exc = ResourceExhaustedError(
            tenant_id="t1",
            unit_name="u1",
            limit=1000.0,
            current=1000.0,
        )
        assert exc._code == "LEX_ERR_GOV_010"


def test_reimport_identity():
    from lexigram.contracts.ai.governance import (
        ResourceExhaustedError,
        ResourceQuota,
        ResourceUnit,
        ResourceUsageResult,
        ResourceUsageSnapshot,
        ResourceWindowKind,
    )
    from lexigram.contracts.ai.governance.resource_unit import (
        ResourceExhaustedError as RE,
        ResourceQuota as RQ,
        ResourceUnit as RU,
        ResourceUsageResult as RUR,
        ResourceUsageSnapshot as RUS,
        ResourceWindowKind as RWK,
    )

    assert ResourceExhaustedError is RE
    assert ResourceUnit is RU
    assert ResourceQuota is RQ
    assert ResourceUsageResult is RUR
    assert ResourceUsageSnapshot is RUS
    assert ResourceWindowKind is RWK


def test_all_importable_from_contracts():
    from lexigram.contracts.ai.governance import (
        ResourceExhaustedError,
        ResourceQuota,
        ResourceUnit,
        ResourceUsageResult,
        ResourceUsageSnapshot,
        ResourceWindowKind,
    )

    assert ResourceUnit is not None
    assert ResourceQuota is not None
    assert ResourceUsageSnapshot is not None
    assert ResourceUsageResult is not None
    assert ResourceExhaustedError is not None
    assert ResourceWindowKind is not None
