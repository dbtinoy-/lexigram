"""Handler fixtures for events testing.

Provides sample event/command/query handlers plus fixtures that pre-register
them on the corresponding test clients.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from lexigram.logging import get_logger
from lexigram.result import Ok
from lexigram.testing.clients.events.fixtures._async import (
    async_fixture as _async_fixture,
)
from lexigram.testing.clients.events.fixtures.models import (
    CreateUserCommand,
    GetUserQuery,
    UserCreatedEvent,
)

logger = get_logger(__name__)

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


# Handler Registration Fixtures


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
