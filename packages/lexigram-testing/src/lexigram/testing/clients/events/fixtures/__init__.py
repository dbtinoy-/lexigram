"""Pytest fixtures for lexigram-events testing.

This package provides comprehensive pytest fixtures for various event-driven
architecture testing scenarios, including events, commands, queries, handlers,
and aggregates. Concerns are grouped into submodules — ``models`` (sample
domain classes), ``beds`` (test beds, clients, buses, cleanup), ``data``
(sample data), ``handlers`` (handler fixtures and registration), and
``scenarios`` (end-to-end scenarios) — and re-exported here.
"""

from __future__ import annotations

from lexigram.testing.clients.events.client import (
    CommandTestClient as CommandTestClient,
)
from lexigram.testing.clients.events.client import (
    EventTestBed as EventTestBed,
)
from lexigram.testing.clients.events.client import (
    EventTestClient as EventTestClient,
)
from lexigram.testing.clients.events.client import (
    EventTestData as EventTestData,
)
from lexigram.testing.clients.events.client import (
    QueryTestClient as QueryTestClient,
)
from lexigram.testing.clients.events.fixtures.beds import (
    command_bus as command_bus,
)
from lexigram.testing.clients.events.fixtures.beds import (
    command_client as command_client,
)
from lexigram.testing.clients.events.fixtures.beds import (
    command_test_bed as command_test_bed,
)
from lexigram.testing.clients.events.fixtures.beds import (
    cqrs_integration_bed as cqrs_integration_bed,
)
from lexigram.testing.clients.events.fixtures.beds import (
    event_bus as event_bus,
)
from lexigram.testing.clients.events.fixtures.beds import (
    event_cleanup as event_cleanup,
)
from lexigram.testing.clients.events.fixtures.beds import (
    event_client as event_client,
)
from lexigram.testing.clients.events.fixtures.beds import (
    event_test_bed as event_test_bed,
)
from lexigram.testing.clients.events.fixtures.beds import (
    full_cqrs_bed as full_cqrs_bed,
)
from lexigram.testing.clients.events.fixtures.beds import (
    query_bus as query_bus,
)
from lexigram.testing.clients.events.fixtures.beds import (
    query_client as query_client,
)
from lexigram.testing.clients.events.fixtures.beds import (
    query_test_bed as query_test_bed,
)
from lexigram.testing.clients.events.fixtures.data import (
    bulk_events as bulk_events,
)
from lexigram.testing.clients.events.fixtures.data import (
    command_test_data as command_test_data,
)
from lexigram.testing.clients.events.fixtures.data import (
    concurrent_commands as concurrent_commands,
)
from lexigram.testing.clients.events.fixtures.data import (
    create_commands as create_commands,
)
from lexigram.testing.clients.events.fixtures.data import (
    delete_commands as delete_commands,
)
from lexigram.testing.clients.events.fixtures.data import (
    detail_queries as detail_queries,
)
from lexigram.testing.clients.events.fixtures.data import (
    domain_events as domain_events,
)
from lexigram.testing.clients.events.fixtures.data import (
    event_sourced_aggregates as event_sourced_aggregates,
)
from lexigram.testing.clients.events.fixtures.data import (
    event_test_data as event_test_data,
)
from lexigram.testing.clients.events.fixtures.data import (
    integration_events as integration_events,
)
from lexigram.testing.clients.events.fixtures.data import (
    list_queries as list_queries,
)
from lexigram.testing.clients.events.fixtures.data import (
    query_test_data as query_test_data,
)
from lexigram.testing.clients.events.fixtures.data import (
    sample_aggregates as sample_aggregates,
)
from lexigram.testing.clients.events.fixtures.data import (
    sample_commands as sample_commands,
)
from lexigram.testing.clients.events.fixtures.data import (
    sample_events as sample_events,
)
from lexigram.testing.clients.events.fixtures.data import (
    sample_queries as sample_queries,
)
from lexigram.testing.clients.events.fixtures.data import (
    update_commands as update_commands,
)
from lexigram.testing.clients.events.fixtures.handlers import (
    command_handlers as command_handlers,
)
from lexigram.testing.clients.events.fixtures.handlers import (
    event_handlers as event_handlers,
)
from lexigram.testing.clients.events.fixtures.handlers import (
    populated_event_bus as populated_event_bus,
)
from lexigram.testing.clients.events.fixtures.handlers import (
    query_handlers as query_handlers,
)
from lexigram.testing.clients.events.fixtures.handlers import (
    registered_command_handlers as registered_command_handlers,
)
from lexigram.testing.clients.events.fixtures.handlers import (
    registered_query_handlers as registered_query_handlers,
)
from lexigram.testing.clients.events.fixtures.models import (
    AggregateRoot as AggregateRoot,
)
from lexigram.testing.clients.events.fixtures.models import (
    Command as Command,
)
from lexigram.testing.clients.events.fixtures.models import (
    CreateOrderCommand as CreateOrderCommand,
)
from lexigram.testing.clients.events.fixtures.models import (
    CreateUserCommand as CreateUserCommand,
)
from lexigram.testing.clients.events.fixtures.models import (
    DeleteUserCommand as DeleteUserCommand,
)
from lexigram.testing.clients.events.fixtures.models import (
    Event as Event,
)
from lexigram.testing.clients.events.fixtures.models import (
    GetOrderQuery as GetOrderQuery,
)
from lexigram.testing.clients.events.fixtures.models import (
    GetUserQuery as GetUserQuery,
)
from lexigram.testing.clients.events.fixtures.models import (
    ListOrdersQuery as ListOrdersQuery,
)
from lexigram.testing.clients.events.fixtures.models import (
    ListUsersQuery as ListUsersQuery,
)
from lexigram.testing.clients.events.fixtures.models import (
    OrderAggregate as OrderAggregate,
)
from lexigram.testing.clients.events.fixtures.models import (
    OrderCreatedEvent as OrderCreatedEvent,
)
from lexigram.testing.clients.events.fixtures.models import (
    OrderShippedIntegrationEvent as OrderShippedIntegrationEvent,
)
from lexigram.testing.clients.events.fixtures.models import (
    Query as Query,
)
from lexigram.testing.clients.events.fixtures.models import (
    TestCommand as TestCommand,
)
from lexigram.testing.clients.events.fixtures.models import (
    TestEvent as TestEvent,
)
from lexigram.testing.clients.events.fixtures.models import (
    UpdateUserCommand as UpdateUserCommand,
)
from lexigram.testing.clients.events.fixtures.models import (
    UserAggregate as UserAggregate,
)
from lexigram.testing.clients.events.fixtures.models import (
    UserCreatedEvent as UserCreatedEvent,
)
from lexigram.testing.clients.events.fixtures.models import (
    UserRegisteredIntegrationEvent as UserRegisteredIntegrationEvent,
)
from lexigram.testing.clients.events.fixtures.models import (
    UserUpdatedEvent as UserUpdatedEvent,
)
from lexigram.testing.clients.events.fixtures.scenarios import (
    event_sourcing_scenario as event_sourcing_scenario,
)

__all__ = [
    "AggregateRoot",
    "Command",
    "CommandTestClient",
    "CreateOrderCommand",
    "CreateUserCommand",
    "DeleteUserCommand",
    "Event",
    "EventTestBed",
    "EventTestClient",
    "EventTestData",
    "GetOrderQuery",
    "GetUserQuery",
    "ListOrdersQuery",
    "ListUsersQuery",
    "OrderAggregate",
    "OrderCreatedEvent",
    "OrderShippedIntegrationEvent",
    "Query",
    "QueryTestClient",
    "TestCommand",
    "TestEvent",
    "UpdateUserCommand",
    "UserAggregate",
    "UserCreatedEvent",
    "UserRegisteredIntegrationEvent",
    "UserUpdatedEvent",
    "bulk_events",
    "command_bus",
    "command_client",
    "command_handlers",
    "command_test_bed",
    "command_test_data",
    "concurrent_commands",
    "cqrs_integration_bed",
    "create_commands",
    "delete_commands",
    "detail_queries",
    "domain_events",
    "event_bus",
    "event_cleanup",
    "event_client",
    "event_sourced_aggregates",
    "event_sourcing_scenario",
    "event_test_bed",
    "event_test_data",
    "full_cqrs_bed",
    "integration_events",
    "list_queries",
    "populated_event_bus",
    "query_bus",
    "query_client",
    "query_handlers",
    "query_test_bed",
    "query_test_data",
    "registered_command_handlers",
    "registered_query_handlers",
    "sample_aggregates",
    "sample_commands",
    "sample_events",
    "sample_queries",
    "update_commands",
]
