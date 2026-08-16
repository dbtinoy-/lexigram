"""
Pytest fixtures for lexigram-events testing.

This module provides comprehensive pytest fixtures for various event-driven
architecture testing scenarios, including events, commands, queries, handlers,
and aggregates.
"""

from __future__ import annotations

# mypy: disable-error-code = annotation-unchecked
from collections.abc import Callable
from types import ModuleType
from typing import Any
from uuid import UUID, uuid4

import pytest

from lexigram.logging import get_logger
from lexigram.result import Ok
from lexigram.testing.clients.events.client import (
    CommandTestClient,
    EventTestBed,
    EventTestClient,
    EventTestData,
    QueryTestClient,
)

logger = get_logger(__name__)

# Shared minimal test event/command/query/aggregate classes (module-level so multiple
# fixtures can reference them without relying on inner-function scope).
try:
    from lexigram.events import AggregateRoot, Command, Event, Query
except (
    ImportError,
    ModuleNotFoundError,
):  # pragma: no cover - defensive fallback for import-time issues

    class Event:  # type: ignore[no-redef]
        pass

    class Command:  # type: ignore[no-redef]
        pass

    class Query:  # type: ignore[no-redef]
        pass

    class AggregateRoot:  # type: ignore[no-redef]
        pass


class UserCreatedEvent(Event):
    aggregate_id: UUID
    user_id: UUID
    name: str
    email: str


class UserUpdatedEvent(Event):
    aggregate_id: UUID
    user_id: UUID
    name: str | None = None
    email: str | None = None


class OrderCreatedEvent(Event):
    aggregate_id: UUID
    order_id: UUID
    user_id: UUID
    amount: float


class UserRegisteredIntegrationEvent(Event):
    aggregate_id: UUID
    user_id: UUID
    email: str
    source: str = "web"


class OrderShippedIntegrationEvent(Event):
    aggregate_id: UUID
    order_id: UUID
    tracking_number: str
    carrier: str


class CreateUserCommand(Command):
    name: str
    email: str


class UpdateUserCommand(Command):
    user_id: UUID
    name: str | None = None
    email: str | None = None


class DeleteUserCommand(Command):
    user_id: UUID


class CreateOrderCommand(Command):
    user_id: UUID
    amount: float
    items: list[dict[str, Any]]


class GetUserQuery(Query):
    user_id: UUID


class ListUsersQuery(Query):
    limit: int = 10
    offset: int = 0
    name_filter: str | None = None


class GetOrderQuery(Query):
    order_id: UUID


class ListOrdersQuery(Query):
    user_id: UUID | None = None
    status: str | None = None
    limit: int = 10


class UserAggregate(AggregateRoot):
    name: str
    email: str
    is_active: bool = True

    def update_name(self, new_name: str) -> Any:
        self.name = new_name
        self.updated_at = getattr(self, "updated_at", None)


class OrderAggregate(AggregateRoot):
    user_id: UUID
    amount: float
    status: str = "pending"

    def complete(self) -> Any:
        if self.status != "pending":
            raise ValueError("Can only complete pending orders")
        self.status = "completed"


class TestEvent(Event):
    aggregate_id: UUID
    index: int
    data: str


class TestCommand(Command):
    index: int
    data: str


# Annotate as ModuleType | None to avoid mypy assignment errors when import fails
pytest_asyncio: ModuleType | None = None
try:
    import pytest_asyncio
except (ImportError, ModuleNotFoundError, AttributeError) as e:
    # Leave as None when unavailable
    import contextlib

    with contextlib.suppress(OSError, ValueError, TypeError):
        logger.debug("pytest_asyncio import unavailable: %s", e)

# Async fixtures must use pytest_asyncio.fixture in strict asyncio mode.
_async_fixture: Callable[..., Any] = (
    pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
)

# Test Bed Fixtures


@_async_fixture
async def event_test_bed() -> Any:
    """Basic event test bed with event bus."""
    async with EventTestBed() as bed:
        yield bed


@_async_fixture
async def command_test_bed() -> Any:
    """Command test bed with command bus."""
    async with EventTestBed() as bed:
        yield bed


@_async_fixture
async def query_test_bed() -> Any:
    """Query test bed with query bus."""
    async with EventTestBed() as bed:
        yield bed


@_async_fixture
async def full_cqrs_bed() -> Any:
    """Full CQRS test bed with all buses."""
    async with EventTestBed() as bed:
        yield bed


# Client Fixtures


@_async_fixture
async def event_client(event_test_bed: Any) -> Any:
    """Event test client."""
    return EventTestClient(event_test_bed)


@_async_fixture
async def command_client(command_test_bed: Any) -> Any:
    """Command test client."""
    return CommandTestClient(command_test_bed)


@_async_fixture
async def query_client(query_test_bed: Any) -> Any:
    """Query test client."""
    return QueryTestClient(query_test_bed)


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


# Handler Fixtures


@pytest.fixture
def event_handlers() -> Any:
    """Sample event handlers for testing."""
    from lexigram.events import (  # - local import for test fixture classes
        EventHandlerProtocol,
    )

    class SendWelcomeEmailHandler(EventHandlerProtocol[UserCreatedEvent]):  # type: ignore[type-arg]
        def __init__(self) -> None:
            self.calls: list[UserCreatedEvent] = []

        async def handle(self, event: UserCreatedEvent) -> Any:
            self.calls.append(event)
            # Simulate sending email
            logger.debug("Sending welcome email to %s", event.email)
            return Ok(None)

    class UpdateUserStatsHandler(EventHandlerProtocol[UserCreatedEvent]):  # type: ignore[type-arg]
        def __init__(self) -> None:
            self.calls: list[UserCreatedEvent] = []

        async def handle(self, event: UserCreatedEvent) -> Any:
            self.calls.append(event)
            # Simulate updating stats
            logger.debug("Updating stats for user %s", event.user_id)
            return Ok(None)

    return [SendWelcomeEmailHandler(), UpdateUserStatsHandler()]


@pytest.fixture
def command_handlers() -> Any:
    """Sample command handlers for testing."""
    from lexigram.events import (  # - local import for test fixture classes
        CommandHandlerProtocol,
    )

    class CreateUserHandler(CommandHandlerProtocol[CreateUserCommand, UUID]):  # type: ignore[type-arg]
        def __init__(self) -> None:
            self.calls: list[Any] = []

        async def handle(self, command: CreateUserCommand) -> UUID:
            self.calls.append(command)
            # Simulate creating user
            user_id = uuid4()
            logger.debug("Created user %s for %s", user_id, command.name)
            return user_id

    return [CreateUserHandler()]


@pytest.fixture
def query_handlers() -> Any:
    """Sample query handlers for testing."""
    from lexigram.events import QueryHandlerProtocol

    class GetUserHandler(QueryHandlerProtocol[GetUserQuery, dict[str, Any]]):  # type: ignore[type-arg]
        def __init__(self) -> None:
            self.calls: list[Any] = []

        async def handle(self, query: GetUserQuery) -> dict[str, Any]:
            self.calls.append(query)
            # Simulate fetching user
            return {
                "user_id": query.user_id,
                "name": "John Doe",
                "email": "john@example.com",
            }

    return [GetUserHandler()]


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


# Bus Fixtures


@_async_fixture
async def event_bus(event_test_bed: Any) -> Any:
    """Event bus instance."""
    return event_test_bed.event_bus


@_async_fixture
async def command_bus(command_test_bed: Any) -> Any:
    """Command bus instance."""
    return command_test_bed.command_bus


@_async_fixture
async def query_bus(query_test_bed: Any) -> Any:
    """Query bus instance."""
    return query_test_bed.query_bus


# Setup/Teardown Fixtures


@pytest.fixture(autouse=True)
async def event_cleanup(
    event_client: Any, command_client: Any, query_client: Any
) -> None:
    """Automatically clean up events, commands, and queries
    before and after each test."""
    # Clean up before test
    event_client.clear_published_events()
    command_client.clear_sent_commands()
    query_client.clear_executed_queries()

    # Clean up after test happens automatically via clients


@_async_fixture
async def populated_event_bus(
    event_client: Any, event_handlers: Any, sample_events: Any
) -> Any:
    """Event bus pre-populated with handlers and events."""
    # Subscribe handlers
    for event in sample_events:
        for handler in event_handlers:
            if hasattr(
                handler,
                "handle",
            ):  # Check if it's a handler for this event type
                try:
                    await event_client.subscribe_handler(type(event), handler)
                except (TypeError, ValueError, AttributeError) as e:
                    get_logger(__name__).debug(
                        "Skipping incompatible handler during fixture subscription: %s",
                        e,
                    )  # Skip incompatible handlers

    yield event_client

    # Cleanup happens automatically


@_async_fixture
async def registered_command_handlers(
    command_client: Any,
    command_handlers: Any,
    sample_commands: Any,
) -> Any:
    """Command bus with registered handlers."""
    # Register handlers
    for command in sample_commands:
        for handler in command_handlers:
            if hasattr(handler, "handle"):
                try:
                    await command_client.register_handler(type(command), handler)
                except (TypeError, ValueError, AttributeError) as e:
                    get_logger(__name__).debug(
                        "Skipping incompatible command handler during registration: %s",
                        e,
                    )  # Skip incompatible handlers

    yield command_client


@_async_fixture
async def registered_query_handlers(
    query_client: Any, query_handlers: Any, sample_queries: Any
) -> Any:
    """Query bus with registered handlers."""
    # Register handlers
    for query in sample_queries:
        for handler in query_handlers:
            if hasattr(handler, "handle"):
                try:
                    await query_client.register_handler(type(query), handler)
                except (TypeError, ValueError, AttributeError) as e:
                    get_logger(__name__).debug(
                        "Skipping incompatible query handler during registration: %s",
                        e,
                    )  # Skip incompatible handlers

    yield query_client


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


# Integration Testing Fixtures


@_async_fixture
async def cqrs_integration_bed() -> Any:
    """Complete CQRS integration test bed."""
    async with EventTestBed() as bed:
        # Could add additional setup here for full CQRS testing
        yield bed


@pytest.fixture
def event_sourcing_scenario() -> Any:
    """Complete event sourcing scenario for testing."""
    from lexigram.events import (  # - local import for test fixtures
        AggregateRoot,
        Event,
    )

    class AccountAggregate(AggregateRoot):
        balance: float = 0.0

        def deposit(self, amount: float) -> Any:
            if amount <= 0:
                raise ValueError("Deposit amount must be positive")
            self.balance += amount

        def withdraw(self, amount: float) -> Any:
            if amount <= 0:
                raise ValueError("Withdrawal amount must be positive")
            if amount > self.balance:
                raise ValueError("Insufficient funds")
            self.balance -= amount

    class DepositedEvent(Event):
        amount: float

    class WithdrawnEvent(Event):
        amount: float

    return {
        "aggregate": AccountAggregate(),
        "events": [
            DepositedEvent(aggregate_id=uuid4(), amount=100.0),
            WithdrawnEvent(aggregate_id=uuid4(), amount=25.0),
            DepositedEvent(aggregate_id=uuid4(), amount=50.0),
        ],
        "expected_balance": 125.0,
    }
