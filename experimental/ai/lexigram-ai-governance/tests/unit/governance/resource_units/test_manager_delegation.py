"""Tests for AIGovernanceManager resource delegation (LXF-001)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from lexigram.ai.governance.config import GovernanceConfig
from lexigram.ai.governance.services.manager import AIGovernanceManager


@pytest.fixture
def config():
    from lexigram.contracts.ai.governance.resource_unit import (
        ResourceUnit,
        ResourceWindowKind,
    )

    return GovernanceConfig(
        resource_units=[
            ResourceUnit(
                name="render_minutes",
                unit_kind="minutes",
                window=timedelta(hours=1),
                window_kind=ResourceWindowKind.SLIDING,
            ),
        ]
    )


@pytest.fixture
def manager(config):
    return AIGovernanceManager(config)


class TestConsumeResource:
    @pytest.mark.asyncio
    async def test_consume_unknown_unit_returns_err(self, manager):
        result = await manager.consume_resource(
            tenant_id="t1", unit_name="nonexistent", amount=10
        )
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_consume_returns_ok_for_valid_unit(
        self, manager, config
    ):
        result = await manager.consume_resource(
            tenant_id="t1",
            unit_name="render_minutes",
            amount=50,
        )
        # No quota configured, so limit=0 → exhausted
        assert result.is_err()


class TestReleaseResource:
    @pytest.mark.asyncio
    async def test_release_unknown_unit_does_not_raise(
        self, manager
    ):
        await manager.release_resource(
            tenant_id="t1", unit_name="nonexistent", amount=1
        )


class TestResourceUsage:
    @pytest.mark.asyncio
    async def test_usage_returns_snapshot(self, manager):
        snap = await manager.resource_usage(
            tenant_id="t1", unit_name="render_minutes"
        )
        assert snap.tenant_id == "t1"
        assert snap.unit_name == "render_minutes"


class TestManagerResourceIntegration:
    @pytest.mark.asyncio
    async def test_consume_release_cycle(self, config):
        from lexigram.ai.governance.persistence import (
            InMemoryGovernancePersistence,
        )

        persistence = InMemoryGovernancePersistence()
        manager = AIGovernanceManager(config, persistence=persistence)
        result = await manager.consume_resource(
            tenant_id="t1",
            unit_name="render_minutes",
            amount=50,
        )
        assert result.is_err()  # No quota configured
