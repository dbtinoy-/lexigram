"""
Testing infrastructure for lexigram-events.

This module provides comprehensive testing utilities for the Lexigram events framework,
including test clients, test beds, fixtures, and mock implementations for event-driven
architecture testing.

Components:
    - EventTestClient: High-level testing client for event operations
    - CommandTestClient: Testing client for command operations
    - QueryTestClient: Testing client for query operations
    - EventTestBed: Async context manager with event buses and handlers
    - EventTestData: Test data models for events, commands, and queries

Example:
    >>> import pytest
    >>> from lexigram.testing.clients.events import EventTestBed, EventTestClient
    >>>
    >>> @pytest.mark.asyncio
    >>> async def test_event_publishing(event_bed, event_client):
    ...     async with event_bed as bed:
    ...         client = EventTestClient(bed)
    ...         await client.publish_event(UserCreatedEvent(user_id="123"))
    ...         events = await client.get_published_events()
    ...         assert len(events) == 1
"""

from __future__ import annotations

from lexigram.testing.clients.events.client import (
    CommandTestClient,
    EventTestBed,
    EventTestClient,
    EventTestData,
    QueryTestClient,
)
from lexigram.testing.clients.events.fixtures import (
    command_bus,
    command_client,
    command_handlers,
    command_test_bed,
    command_test_data,
    create_commands,
    delete_commands,
    detail_queries,
    domain_events,
    # Bus fixtures
    event_bus,
    # Client fixtures
    event_client,
    # Handler fixtures
    event_handlers,
    event_sourced_aggregates,
    # Test bed fixtures
    event_test_bed,
    # Data fixtures
    event_test_data,
    full_cqrs_bed,
    integration_events,
    list_queries,
    query_bus,
    query_client,
    query_handlers,
    query_test_bed,
    query_test_data,
    # Aggregate fixtures
    sample_aggregates,
    # Command fixtures
    sample_commands,
    # Event fixtures
    sample_events,
    # Query fixtures
    sample_queries,
    update_commands,
)

__all__ = [
    "CommandTestClient",
    "EventTestBed",
    "EventTestClient",
    "EventTestData",
    "QueryTestClient",
    "command_bus",
    "command_client",
    "command_handlers",
    "command_test_bed",
    "command_test_data",
    "create_commands",
    "delete_commands",
    "detail_queries",
    "domain_events",
    "event_bus",
    "event_client",
    "event_handlers",
    "event_sourced_aggregates",
    "event_test_bed",
    "event_test_data",
    "full_cqrs_bed",
    "integration_events",
    "list_queries",
    "query_bus",
    "query_client",
    "query_handlers",
    "query_test_bed",
    "query_test_data",
    "sample_aggregates",
    "sample_commands",
    "sample_events",
    "sample_queries",
    "update_commands",
]
