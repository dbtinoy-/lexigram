"""Events + SQL event-driven state change scenario.

Packages under test: lexigram-events, lexigram-sql
Infrastructure: in-memory SQLite + in-process event bus (no live service)

Scenario:
1. Boot a minimal application with EventsModule + DatabaseModule.
2. Publish a domain event onto the real in-process EventBus.
3. Assert that the registered event handler updates aggregate state in the DB.
4. Publish a sequence of events and verify they are applied in order.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.integration.scenarios._bed import scenario_bed
from tests.integration.scenarios.scenario_apps import (
    OrderConfirmed,
    OrderCreated,
    OrderDelivered,
    OrderPaid,
    OrderShipped,
    create_events_app,
)

if TYPE_CHECKING:
    from tests.integration.scenarios._bed import ScenarioTestBed

pytestmark = [pytest.mark.integration, pytest.mark.scenario]


@pytest.fixture
async def bed() -> "ScenarioTestBed":
    """Boot a minimal Events + SQL test application."""
    async with scenario_bed(create_events_app) as scenario:
        yield scenario


class TestEventsSql:
    """Events + SQL: event-driven state changes persisted to SQLite."""

    async def test_published_event_persists_state(self, bed: "ScenarioTestBed") -> None:
        """Publishing an event causes the handler to write state to the DB."""
        aggregate_id = "agg-001"
        await bed.events.publish(
            OrderCreated(aggregate_id=aggregate_id, aggregate_type="order")
        )
        await bed.events.drain()

        row = await bed.db.fetch_one(
            "SELECT status FROM orders WHERE id = ?", aggregate_id
        )
        assert row is not None
        assert row["status"] == "created"

    async def test_event_handler_updates_state(self, bed: "ScenarioTestBed") -> None:
        """Events transition the aggregate from ``created`` to ``paid``."""
        aggregate_id = "agg-002"
        for event in (
            OrderCreated(aggregate_id=aggregate_id, aggregate_type="order"),
            OrderPaid(aggregate_id=aggregate_id, aggregate_type="order"),
        ):
            await bed.events.publish(event)
        await bed.events.drain()

        row = await bed.db.fetch_one(
            "SELECT status FROM orders WHERE id = ?", aggregate_id
        )
        assert row is not None
        assert row["status"] == "paid"

    async def test_event_ordering_preserved(self, bed: "ScenarioTestBed") -> None:
        """Rapid sequential publishes are applied in publication order."""
        aggregate_id = "agg-003"
        for event_type in (
            OrderCreated,
            OrderConfirmed,
            OrderShipped,
            OrderDelivered,
        ):
            await bed.events.publish(
                event_type(aggregate_id=aggregate_id, aggregate_type="order")
            )
        await bed.events.drain()

        row = await bed.db.fetch_one(
            "SELECT status FROM orders WHERE id = ?", aggregate_id
        )
        assert row is not None
        assert row["status"] == "delivered"
