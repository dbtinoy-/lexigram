"""Test data container for event testing scenarios."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from lexigram.events import AggregateRoot, Command, Event, Query


class EventTestData:
    """Test data container for event testing scenarios.

    Provides structured test data for various event-driven testing scenarios,
    including domain events, commands, queries, and aggregates.
    """

    def __init__(self, prefix: str = "test"):
        """Initialize test data with prefix."""
        self.prefix = prefix
        self._events: list[Event] = []
        self._commands: list[Command] = []
        self._queries: list[Query] = []
        self._aggregates: dict[str, AggregateRoot] = {}

    def add_event(self, event: Event) -> None:
        """Add an event to the test data."""
        self._events.append(event)

    def add_command(self, command: Command) -> None:
        """Add a command to the test data."""
        self._commands.append(command)

    def add_query(self, query: Query) -> None:
        """Add a query to the test data."""
        self._queries.append(query)

    def add_aggregate(self, key: str, aggregate: AggregateRoot) -> None:
        """Add an aggregate to the test data."""
        self._aggregates[key] = aggregate

    def get_events(self, event_type: type[Event] | None = None) -> list[Event]:
        """Get events, optionally filtered by type."""
        if event_type:
            return list(filter(lambda e: isinstance(e, event_type), self._events))
        return self._events.copy()

    def get_commands(self, command_type: type[Command] | None = None) -> list[Command]:
        """Get commands, optionally filtered by type."""
        if command_type:
            return list(filter(lambda c: isinstance(c, command_type), self._commands))
        return self._commands.copy()

    def get_queries(self, query_type: type[Query] | None = None) -> list[Query]:
        """Get queries, optionally filtered by type."""
        if query_type:
            return list(filter(lambda q: isinstance(q, query_type), self._queries))
        return self._queries.copy()

    def get_aggregate(self, key: str) -> AggregateRoot | None:
        """Get an aggregate by key."""
        return self._aggregates.get(key)

    def clear(self) -> None:
        """Clear all test data."""
        self._events.clear()
        self._commands.clear()
        self._queries.clear()
        self._aggregates.clear()

    @classmethod
    def create_sample_events(cls, prefix: str = "sample") -> EventTestData:
        """Create test data with sample events."""
        data = cls(prefix)

        # Create sample events
        from uuid import uuid4

        from lexigram.events import Event

        class UserCreatedEvent(Event):
            user_id: UUID
            name: str
            email: str

        class OrderPlacedEvent(Event):
            order_id: UUID
            user_id: UUID
            amount: float

        def _make_event(event_cls: type[Event], **kwargs: Any) -> Event:
            from uuid import uuid4

            data = {
                "aggregate_id": kwargs.get("aggregate_id", uuid4()),
                "aggregate_type": kwargs.get("aggregate_type", "TestAggregate"),
                "version": kwargs.get("version", 0),
                "event_type": kwargs.get("event_type"),
                "sequence_number": kwargs.get("sequence_number"),
                "actor_id": kwargs.get("actor_id"),
            }
            data.update(kwargs)
            return event_cls(**data)

        data.add_event(
            _make_event(
                UserCreatedEvent,
                aggregate_id=uuid4(),
                user_id=uuid4(),
                name="John Doe",
                email="john@example.com",
            ),
        )

        data.add_event(
            _make_event(
                OrderPlacedEvent,
                aggregate_id=uuid4(),
                order_id=uuid4(),
                user_id=uuid4(),
                amount=99.99,
            ),
        )

        return data

    @classmethod
    def create_sample_commands(cls, prefix: str = "sample") -> EventTestData:
        """Create test data with sample commands."""
        data = cls(prefix)

        # Create sample commands
        from lexigram.events import Command

        class CreateUserCommand(Command):
            name: str
            email: str

        class PlaceOrderCommand(Command):
            user_id: UUID
            amount: float

        data.add_command(
            CreateUserCommand(
                name="Jane Doe",
                email="jane@example.com",
                target_aggregate_id=uuid4(),
                expected_version=0,
            ),
        )

        data.add_command(
            PlaceOrderCommand(
                user_id=uuid4(),
                amount=149.99,
                target_aggregate_id=uuid4(),
                expected_version=0,
            ),
        )

        return data

    @classmethod
    def create_sample_queries(cls, prefix: str = "sample") -> EventTestData:
        """Create test data with sample queries."""
        data = cls(prefix)

        # Create sample queries
        from lexigram.events import Query

        class GetUserQuery(Query):
            user_id: UUID

        class ListOrdersQuery(Query):
            user_id: UUID | None = None
            limit: int = 10

        data.add_query(
            GetUserQuery(  # type: ignore[call-arg]
                user_id=uuid4(),
                include_deleted=False,
                cache_key=None,
                skip_cache=False,
            ),
        )
        data.add_query(
            ListOrdersQuery(  # type: ignore[call-arg]
                limit=20,
                include_deleted=False,
                cache_key=None,
                skip_cache=False,
            ),
        )

        return data
