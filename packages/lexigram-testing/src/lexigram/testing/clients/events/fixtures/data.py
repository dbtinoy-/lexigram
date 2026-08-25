"""Sample data fixtures for events testing.

Provides sample events, commands, queries, aggregates, and bulk data for
event-driven architecture testing scenarios.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from lexigram.testing.clients.events.client import EventTestData
from lexigram.testing.clients.events.fixtures.models import (
    CreateOrderCommand,
    CreateUserCommand,
    DeleteUserCommand,
    GetOrderQuery,
    GetUserQuery,
    ListOrdersQuery,
    ListUsersQuery,
    OrderAggregate,
    OrderCreatedEvent,
    OrderShippedIntegrationEvent,
    TestCommand,
    TestEvent,
    UpdateUserCommand,
    UserAggregate,
    UserCreatedEvent,
    UserRegisteredIntegrationEvent,
    UserUpdatedEvent,
)

# Data Fixtures


@pytest.fixture
def event_test_data() -> Any:
    """Basic event test data."""
    return EventTestData.create_sample_events("test")


@pytest.fixture
def command_test_data() -> Any:
    """Basic command test data."""
    return EventTestData.create_sample_commands("test")


@pytest.fixture
def query_test_data() -> Any:
    """Basic query test data."""
    return EventTestData.create_sample_queries("test")


# Event Fixtures


@pytest.fixture
def sample_events() -> Any:
    """Sample domain events for testing."""

    return [
        UserCreatedEvent(
            aggregate_id=uuid4(),
            user_id=uuid4(),
            name="Alice Johnson",
            email="alice@example.com",
        ),
        UserUpdatedEvent(
            aggregate_id=uuid4(),
            user_id=uuid4(),
            name="Alice Smith",
        ),
        OrderCreatedEvent(
            aggregate_id=uuid4(),
            order_id=uuid4(),
            user_id=uuid4(),
            amount=99.99,
        ),
    ]


@pytest.fixture
def domain_events(sample_events: Any) -> Any:
    """Domain events for testing."""
    return sample_events


@pytest.fixture
def integration_events() -> Any:
    """Integration events for testing."""

    return [
        UserRegisteredIntegrationEvent(
            aggregate_id=uuid4(),
            user_id=uuid4(),
            email="user@example.com",
        ),
        OrderShippedIntegrationEvent(
            aggregate_id=uuid4(),
            order_id=uuid4(),
            tracking_number="TR123456",
            carrier="UPS",
        ),
    ]


# Command Fixtures


@pytest.fixture
def sample_commands() -> Any:
    """Sample commands for testing."""

    return [
        CreateUserCommand(name="Bob Wilson", email="bob@example.com"),
        UpdateUserCommand(user_id=uuid4(), name="Bob Smith"),
        DeleteUserCommand(user_id=uuid4()),
        CreateOrderCommand(
            user_id=uuid4(),
            amount=149.99,
            items=[{"product_id": "prod1", "quantity": 2}],
        ),
    ]


@pytest.fixture
def create_commands(sample_commands: Any) -> Any:
    """Create commands for testing."""
    return list(
        filter(lambda c: c.__class__.__name__.startswith("Create"), sample_commands),
    )


@pytest.fixture
def update_commands(sample_commands: Any) -> Any:
    """Update commands for testing."""
    return list(
        filter(lambda c: c.__class__.__name__.startswith("Update"), sample_commands),
    )


@pytest.fixture
def delete_commands(sample_commands: Any) -> Any:
    """Delete commands for testing."""
    return list(
        filter(lambda c: c.__class__.__name__.startswith("Delete"), sample_commands),
    )


# Query Fixtures


@pytest.fixture
def sample_queries() -> Any:
    """Sample queries for testing."""

    return [
        GetUserQuery(user_id=uuid4()),  # type: ignore[call-arg]
        ListUsersQuery(limit=20, name_filter="John"),  # type: ignore[call-arg]
        GetOrderQuery(order_id=uuid4()),  # type: ignore[call-arg]
        ListOrdersQuery(user_id=uuid4(), status="pending", limit=5),  # type: ignore[call-arg]
    ]


@pytest.fixture
def list_queries(sample_queries: Any) -> Any:
    """List queries for testing."""
    return list(
        filter(lambda q: q.__class__.__name__.startswith("List"), sample_queries),
    )


@pytest.fixture
def detail_queries(sample_queries: Any) -> Any:
    """Detail queries for testing."""
    return list(
        filter(lambda q: q.__class__.__name__.startswith("Get"), sample_queries),
    )


# Aggregate Fixtures


@pytest.fixture
def sample_aggregates() -> Any:
    """Sample aggregates for testing."""

    user = UserAggregate(name="Alice", email="alice@example.com")
    order = OrderAggregate(user_id=uuid4(), amount=99.99)

    return [user, order]


@pytest.fixture
def event_sourced_aggregates(sample_aggregates: Any) -> Any:
    """Event-sourced aggregates for testing."""
    return sample_aggregates


# Performance Testing Fixtures


@pytest.fixture
def bulk_events() -> Any:
    """Large number of events for performance testing."""

    return [
        TestEvent(aggregate_id=uuid4(), index=i, data=f"test_data_{i}")
        for i in range(1000)
    ]


@pytest.fixture
def concurrent_commands() -> Any:
    """Commands for concurrent execution testing."""

    return [TestCommand(index=i, data=f"concurrent_data_{i}") for i in range(50)]
