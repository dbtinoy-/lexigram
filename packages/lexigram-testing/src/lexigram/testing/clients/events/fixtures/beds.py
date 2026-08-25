"""Test bed, client, and bus fixtures for events testing.

Provides the lifecycle fixtures that open an :class:`EventTestBed`, expose
the event/command/query clients and buses, and clean up between tests.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.testing.clients.events.client import (
    CommandTestClient,
    EventTestBed,
    EventTestClient,
    QueryTestClient,
)
from lexigram.testing.clients.events.fixtures._async import (
    async_fixture as _async_fixture,
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


# Integration Testing Fixtures


@_async_fixture
async def cqrs_integration_bed() -> Any:
    """Complete CQRS integration test bed."""
    async with EventTestBed() as bed:
        # Could add additional setup here for full CQRS testing
        yield bed
