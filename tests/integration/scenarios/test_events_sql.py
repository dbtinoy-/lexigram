from __future__ import annotations

"""Events + SQL event-driven state change scenario.

Packages under test: lexigram-events, lexigram-sql
Infrastructure: PostgreSQL

Scenario:
1. Boot a minimal application with EventsProvider + SqlProvider.
2. Publish a domain event onto the in-process EventBus.
3. Assert that the registered event handler updates aggregate state in the DB.
4. Publish a sequence of events and verify they are applied in order.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.scenario, pytest.mark.requires_postgres]


class TestEventsSql:
    """Events + SQL: event-driven state changes persisted to PostgreSQL.

    Boots a minimal application with EventsProvider + SqlProvider,
    publishes domain events via the EventBus, and asserts that event
    handlers durably update aggregate state in the database.
    """

    @pytest.fixture
    async def bed(self) -> None:
        """Boot a minimal Events + SQL test application.

        Yields:
            AppTestBed configured with EventsProvider + SqlProvider.
        """
        pytest.skip(
            "TODO: implement create_events_app factory in conftest.py "
            "and wire AppTestBed.from_factory(create_events_app)"
        )

    async def test_published_event_persists_state(self, bed: object) -> None:
        """Publishing a domain event causes the handler to write state to the DB.

        After the event is processed, the aggregate row in the database
        should reflect the change encoded in the event payload.

        Args:
            bed: Booted AppTestBed with EventBus and live DB.
        """
        aggregate_id = "agg-001"
        await bed.events.publish(  # type: ignore[attr-defined]
            "order.created",
            {"aggregate_id": aggregate_id, "total": 99.99},
        )
        await bed.events.drain()  # type: ignore[attr-defined]

        row = await bed.db.fetch_one(  # type: ignore[attr-defined]
            "SELECT status FROM orders WHERE id = $1", aggregate_id
        )
        assert row is not None
        assert row["status"] == "created"

    async def test_event_handler_updates_state(self, bed: object) -> None:
        """An event handler correctly transitions aggregate state.

        Publishing an ``order.paid`` event after ``order.created`` should
        transition the aggregate's status field from ``created`` to ``paid``.

        Args:
            bed: Booted AppTestBed with EventBus and live DB.
        """
        aggregate_id = "agg-002"
        await bed.events.publish("order.created", {"aggregate_id": aggregate_id, "total": 50.00})  # type: ignore[attr-defined]
        await bed.events.publish("order.paid", {"aggregate_id": aggregate_id})  # type: ignore[attr-defined]
        await bed.events.drain()  # type: ignore[attr-defined]

        row = await bed.db.fetch_one(  # type: ignore[attr-defined]
            "SELECT status FROM orders WHERE id = $1", aggregate_id
        )
        assert row is not None
        assert row["status"] == "paid"

    async def test_event_ordering_preserved(self, bed: object) -> None:
        """Events published to the same aggregate are applied in publication order.

        Rapid sequential publishes must not reorder; the final persisted state
        must reflect the last event in the sequence.

        Args:
            bed: Booted AppTestBed with EventBus and live DB.
        """
        aggregate_id = "agg-003"
        states = ["created", "confirmed", "shipped", "delivered"]
        for state in states:
            await bed.events.publish(f"order.{state}", {"aggregate_id": aggregate_id})  # type: ignore[attr-defined]
        await bed.events.drain()  # type: ignore[attr-defined]

        row = await bed.db.fetch_one(  # type: ignore[attr-defined]
            "SELECT status FROM orders WHERE id = $1", aggregate_id
        )
        assert row is not None
        assert row["status"] == "delivered"
