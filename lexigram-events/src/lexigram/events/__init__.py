"""Lexigram Events - Event Sourcing and CQRS for Python.

This package provides a complete Event Sourcing and CQRS implementation
for building scalable, event-driven applications.

Core Features:
    - **Event Sourcing**: Store all changes as immutable events
    - **CQRS**: Separate read and write models for scalability
    - **Aggregate Pattern**: DDD building blocks for domain modeling
    - **Event Store**: Multiple backends (PostgreSQL, MongoDB, In-Memory)
    - **Sagas**: Long-running business processes
    - **Projections**: Build read models from events
    - **Streaming**: Real-time event streaming with WebSocket support
    - **Middleware**: Extensible middleware pipeline

Basic Usage:
    ```python
    from lexigram.contracts.domain import DomainEvent
    from lexigram.events import (
        Command, Query, Event,
        CommandBusImpl, QueryBusImpl, EventBusImpl,
        AggregateRoot, InMemoryEventStore,
    )

    # Define events
    class UserCreated(DomainEvent):
        user_id: UUID
        name: str
        email: str
    ```

Module Structure:
    - messages: Command, Query, Event base classes
    - buses: CommandBusImpl, QueryBusImpl, EventBusImpl
    - stores: Event storage backends
    - aggregates: AggregateRoot, Entity, ValueObject
    - repository: Event sourcing repository
    - handlers: Handler registration and discovery
    - middleware: Middleware pipeline components
    - projections: Read model management
    - streaming: Event streaming and WebSocket
    - adapters: Message broker adapters (RabbitMQ, Kafka, Azure)
    - schema: Schema registry and evolution
"""

from __future__ import annotations

import importlib.metadata
import sys
from typing import TYPE_CHECKING, Any

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from lexigram.events.constants import __version__ as __version__

# Lazy loading to avoid circular imports

if TYPE_CHECKING:
    from lexigram.contracts.data import ReadOnlyRepositoryProtocol
    from lexigram.contracts.domain import DomainEvent
    from lexigram.contracts.events import (
        AggregateFactoryProtocol,
        CommandBusProtocol,
        CommandHandlerProtocol,
        DomainEventPublisherProtocol,
        EventBusProtocol,
        EventHandlerProtocol,
        EventStoreProtocol,
        MultiEventHandlerProtocol,
        ProjectionProtocol,
        QueryBusProtocol,
        QueryHandlerProtocol,
        SnapshotStoreProtocol,
    )
    from lexigram.contracts.workflow import (
        SagaManagerProtocol,
        SagaProtocol,
    )
    from lexigram.events.aggregates.aggregate import AggregateRoot
    from lexigram.events.aggregates.entity import Entity
    from lexigram.events.aggregates.value_object import ValueObject
    from lexigram.events.buses.command import CommandBusImpl
    from lexigram.events.buses.event import (
        DispatchResult,
        EventBusImpl,
    )
    from lexigram.events.buses.query import QueryBusImpl
    from lexigram.events.config import (
        CommandBusConfig,
        EventBusConfig,
        EventsConfig,
        InMemoryEventStoreConfig,
        MongoDBEventStoreConfig,
        PostgresEventStoreConfig,
        QueryBusConfig,
        SnapshotConfig,
    )
    from lexigram.events.decorators.handlers import (
        command_handler,
        event_handler,
        query_handler,
    )
    from lexigram.events.di import EventsProvider
    from lexigram.events.exceptions import (
        AggregateNotFoundError,
        ConcurrencyError,
        EventError,
        EventLoadError,
        EventPersistenceError,
        EventStoreConnectionError,
        EventStoreError,
        HandlerNotFoundError,
        ProjectionBuildError,
        ProjectionNotFoundError,
        SchemaError,
        SecurityError,
        StreamingError,
        StreamNotFoundError,
        WebhookDeliveryError,
    )
    from lexigram.events.handlers.registry import (
        HandlerRegistry,
    )
    from lexigram.events.messages.base import (
        Message,
        MessageMetadata,
    )
    from lexigram.events.messages.command import (
        Command,
        IdempotentCommand,
    )
    from lexigram.events.messages.event import (
        Event,
        IntegrationEvent,
    )
    from lexigram.events.messages.query import (
        PagedResult,
        PaginatedQuery,
        Query,
    )
    from lexigram.events.middleware.base import (
        AbstractMiddleware,
        NextHandler,
    )
    from lexigram.events.protocols import (
        EventFilterProtocol,
        EventSerializerProtocol,
    )
    from lexigram.events.repository.base import (
        AbstractReadOnlyRepository,
        AbstractRepository,
    )
    from lexigram.events.repository.event_sourcing import EventSourcingRepository
    from lexigram.events.stores import (
        HAS_MONGODB,
        HAS_POSTGRES,
        HAS_SQLITE,
        PostgresEventStore,
        PostgresSnapshotStore,
    )
    from lexigram.events.stores.base import (
        AbstractEventStore,
        AbstractSnapshotStore,
    )
    from lexigram.events.stores.memory import (
        InMemoryEventStore,
        InMemorySnapshotStore,
    )
    from lexigram.events.stores.redis import RedisEventStore
    from lexigram.events.stores.snapshot import SnapshotManager
    from lexigram.events.types import (
        AggregateStatus,
        Checkpoint,
        CommandResult,
        EventEnvelope,
        EventStoreBackend,
        HandlerInfo,
        MessageType,
        MiddlewareInfo,
        ProjectionState,
        QueryResult,
        Snapshot,
        SnapshotStrategy,
        StreamInfo,
        StreamPosition,
    )
    from lexigram.events.version_skew import (
        KnownEventSetRegistry,
        VersionAwareSubscription,
        known_events,
    )
    from lexigram.events.webhooks.dispatcher import (
        WebhookDispatcher,
        WebhookEndpoint,
    )

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # Module
    "EventsModule": ("lexigram.events.module", "EventsModule"),
    # Buses (concrete implementations — primary names for test/runtime use)
    "CommandBusProtocol": ("lexigram.contracts.events", "CommandBusProtocol"),
    "CommandBusImpl": ("lexigram.events.buses.command", "CommandBusImpl"),
    "CommandBus": ("lexigram.contracts", "CommandBusProtocol"),
    "EventBusProtocol": ("lexigram.contracts.events", "EventBusProtocol"),
    "EventBusImpl": ("lexigram.events.buses.event", "EventBusImpl"),
    "EventBus": ("lexigram.contracts", "EventBusProtocol"),
    "QueryBusProtocol": ("lexigram.contracts.events", "QueryBusProtocol"),
    "QueryBusImpl": ("lexigram.events.buses.query", "QueryBusImpl"),
    "QueryBus": ("lexigram.contracts", "QueryBusProtocol"),
    "command_handler": ("lexigram.events.decorators.handlers", "command_handler"),
    "event_handler": ("lexigram.events.decorators.handlers", "event_handler"),
    "query_handler": ("lexigram.events.decorators.handlers", "query_handler"),
    "NextHandler": ("lexigram.events.middleware.base", "NextHandler"),
    "AbstractMiddleware": ("lexigram.events.middleware.base", "AbstractMiddleware"),
    # Config
    "CommandBusConfig": ("lexigram.events.config", "CommandBusConfig"),
    "EventBusConfig": ("lexigram.events.config", "EventBusConfig"),
    "EventsConfig": ("lexigram.events.config", "EventsConfig"),
    "InMemoryEventStoreConfig": ("lexigram.events.config", "InMemoryEventStoreConfig"),
    "MongoDBEventStoreConfig": ("lexigram.events.config", "MongoDBEventStoreConfig"),
    "PostgresEventStoreConfig": ("lexigram.events.config", "PostgresEventStoreConfig"),
    "PostgresEventStore": ("lexigram.events.stores", "PostgresEventStore"),
    "PostgresSnapshotStore": ("lexigram.events.stores", "PostgresSnapshotStore"),
    "RedisEventStore": ("lexigram.events.stores.redis", "RedisEventStore"),
    "QueryBusConfig": ("lexigram.events.config", "QueryBusConfig"),
    "SnapshotConfig": ("lexigram.events.config", "SnapshotConfig"),
    # Exceptions
    "AggregateNotFoundError": ("lexigram.events.exceptions", "AggregateNotFoundError"),
    "CommandExecutionError": ("lexigram.events.exceptions", "CommandExecutionError"),
    "ConcurrencyError": ("lexigram.events.exceptions", "ConcurrencyError"),
    "DuplicateHandlerError": ("lexigram.events.exceptions", "DuplicateHandlerError"),
    "EventError": ("lexigram.events.exceptions", "EventError"),
    "EventLoadError": ("lexigram.events.exceptions", "EventLoadError"),
    "EventPersistenceError": ("lexigram.events.exceptions", "EventPersistenceError"),
    "EventStoreConnectionError": (
        "lexigram.events.exceptions",
        "EventStoreConnectionError",
    ),
    "EventStoreError": ("lexigram.events.exceptions", "EventStoreError"),
    "HandlerNotFoundError": ("lexigram.events.exceptions", "HandlerNotFoundError"),
    "ProjectionBuildError": ("lexigram.events.exceptions", "ProjectionBuildError"),
    "ProjectionNotFoundError": (
        "lexigram.events.exceptions",
        "ProjectionNotFoundError",
    ),
    "QueryExecutionError": ("lexigram.events.exceptions", "QueryExecutionError"),
    "SchemaError": ("lexigram.events.exceptions", "SchemaError"),
    "SecurityError": ("lexigram.events.exceptions", "SecurityError"),
    "StreamingError": ("lexigram.events.exceptions", "StreamingError"),
    "StreamNotFoundError": ("lexigram.events.exceptions", "StreamNotFoundError"),
    "WebhookDeliveryError": ("lexigram.events.exceptions", "WebhookDeliveryError"),
    # Webhooks
    "WebhookDispatcher": ("lexigram.events.webhooks.dispatcher", "WebhookDispatcher"),
    "WebhookEndpoint": ("lexigram.events.webhooks.dispatcher", "WebhookEndpoint"),
    # Messages
    "Command": ("lexigram.events.messages.command", "Command"),
    "Event": ("lexigram.events.messages.event", "Event"),
    # Domain event base from contracts for convenience
    "DomainEvent": ("lexigram.contracts.domain", "DomainEvent"),
    "IdempotentCommand": ("lexigram.events.messages.command", "IdempotentCommand"),
    "IntegrationEvent": ("lexigram.events.messages.event", "IntegrationEvent"),
    "Message": ("lexigram.events.messages.base", "Message"),
    "MessageMetadata": ("lexigram.events.messages.base", "MessageMetadata"),
    "PagedResult": ("lexigram.events.messages.query", "PagedResult"),
    "PaginatedQuery": ("lexigram.events.messages.query", "PaginatedQuery"),
    "Query": ("lexigram.events.messages.query", "Query"),
    # Stores
    "HAS_MONGODB": ("lexigram.events.stores", "HAS_MONGODB"),
    "HAS_POSTGRES": ("lexigram.events.stores", "HAS_POSTGRES"),
    "HAS_SQLITE": ("lexigram.events.stores", "HAS_SQLITE"),
    "AbstractEventStore": ("lexigram.events.stores.base", "AbstractEventStore"),
    "InMemoryEventStore": ("lexigram.events.stores.memory", "InMemoryEventStore"),
    "InMemorySnapshotStore": ("lexigram.events.stores.memory", "InMemorySnapshotStore"),
    "SnapshotManager": ("lexigram.events.stores.snapshot", "SnapshotManager"),
    "AbstractSnapshotStore": ("lexigram.events.stores.base", "AbstractSnapshotStore"),
    # DTOs
    "Checkpoint": ("lexigram.events.types", "Checkpoint"),
    "EventEnvelope": ("lexigram.events.types", "EventEnvelope"),
    "Snapshot": ("lexigram.events.types", "Snapshot"),
    "StreamInfo": ("lexigram.events.types", "StreamInfo"),
    # Enums
    "AggregateStatus": ("lexigram.events.types", "AggregateStatus"),
    "EventStoreBackend": ("lexigram.events.types", "EventStoreBackend"),
    "MessageType": ("lexigram.events.types", "MessageType"),
    "ProjectionState": ("lexigram.events.types", "ProjectionState"),
    "SnapshotStrategy": ("lexigram.events.types", "SnapshotStrategy"),
    "StreamPosition": ("lexigram.events.types", "StreamPosition"),
    # Results
    "CommandResult": ("lexigram.events.types", "CommandResult"),
    "DispatchResult": ("lexigram.events.buses.event", "DispatchResult"),
    "HandlerInfo": ("lexigram.events.types", "HandlerInfo"),
    "MiddlewareInfo": ("lexigram.events.types", "MiddlewareInfo"),
    "QueryResult": ("lexigram.events.types", "QueryResult"),
    # Aggregates
    "AggregateRoot": ("lexigram.events.aggregates.aggregate", "AggregateRoot"),
    "Entity": ("lexigram.events.aggregates.entity", "Entity"),
    "ValueObject": ("lexigram.events.aggregates.value_object", "ValueObject"),
    # Handlers
    "CommandHandlerProtocol": (
        "lexigram.events.handlers.registry",
        "CommandHandlerProtocol",
    ),
    "EventHandlerProtocol": (
        "lexigram.events.handlers.registry",
        "EventHandlerProtocol",
    ),
    "HandlerRegistry": ("lexigram.events.handlers.registry", "HandlerRegistry"),
    "QueryHandlerProtocol": (
        "lexigram.events.handlers.registry",
        "QueryHandlerProtocol",
    ),
    "clear_handler_registry": (
        "lexigram.events.handlers.registry",
        "clear_handler_registry",
    ),
    # RepositoryProtocol
    "EventSourcingRepository": (
        "lexigram.events.repository.event_sourcing",
        "EventSourcingRepository",
    ),
    "RepositoryProtocol": ("lexigram.contracts.data", "RepositoryProtocol"),
    "AbstractRepository": ("lexigram.events.repository.base", "AbstractRepository"),
    "AbstractReadOnlyRepository": (
        "lexigram.events.repository.base",
        "AbstractReadOnlyRepository",
    ),
    # Provider
    "EventsProvider": ("lexigram.events.di", "EventsProvider"),
    # Version skew
    "VersionAwareSubscription": (
        "lexigram.events.version_skew.subscription",
        "VersionAwareSubscription",
    ),
    "KnownEventSetRegistry": (
        "lexigram.events.version_skew.registry",
        "KnownEventSetRegistry",
    ),
    "known_events": (
        "lexigram.events.version_skew.decorator",
        "known_events",
    ),
    # Contracts
    "AggregateFactoryProtocol": (
        "lexigram.contracts.events",
        "AggregateFactoryProtocol",
    ),
    "DomainEventPublisherProtocol": (
        "lexigram.contracts.events",
        "DomainEventPublisherProtocol",
    ),
    "EventStoreProtocol": ("lexigram.contracts.events", "EventStoreProtocol"),
    "MultiEventHandlerProtocol": (
        "lexigram.contracts.events",
        "MultiEventHandlerProtocol",
    ),
    "ProjectionProtocol": ("lexigram.contracts.events", "ProjectionProtocol"),
    "ReadOnlyRepositoryProtocol": (
        "lexigram.contracts.data",
        "ReadOnlyRepositoryProtocol",
    ),
    "SagaProtocol": ("lexigram.contracts.workflow", "SagaProtocol"),
    "SagaManagerProtocol": ("lexigram.contracts.workflow", "SagaManagerProtocol"),
    "SnapshotStoreProtocol": ("lexigram.contracts.events", "SnapshotStoreProtocol"),
    # Optional stores (sqlite, postgres, mongodb — available if extras installed)
    "SqliteConfig": ("lexigram.events.stores.sqlite", "SqliteConfig"),
    "SqliteEventStore": ("lexigram.events.stores.sqlite", "SqliteEventStore"),
    "SqliteSnapshotStore": ("lexigram.events.stores.sqlite", "SqliteSnapshotStore"),
    "MongoDBConfig": ("lexigram.events.stores.mongodb", "MongoDBConfig"),
    "MongoDBEventStore": ("lexigram.events.stores.mongodb", "MongoDBEventStore"),
    "MongoDBSnapshotStore": ("lexigram.events.stores.mongodb", "MongoDBSnapshotStore"),
    # Internal protocols
    "EventSerializerProtocol": ("lexigram.events.protocols", "EventSerializerProtocol"),
    "EventFilterProtocol": ("lexigram.events.protocols", "EventFilterProtocol"),
    # Events (operational meta-events)
    "EventPublishedEvent": ("lexigram.events.events", "EventPublishedEvent"),
    "ProjectionUpdatedEvent": ("lexigram.events.events", "ProjectionUpdatedEvent"),
    # Hooks
    "EventHandledHook": ("lexigram.events.hooks", "EventHandledHook"),
    "EventPublishedHook": ("lexigram.events.hooks", "EventPublishedHook"),
    "EventStoredHook": ("lexigram.events.hooks", "EventStoredHook"),
    # Reactive bridges
    "from_bus": ("lexigram.events.reactive", "from_bus"),
    "from_store": ("lexigram.events.reactive", "from_store"),
    "retry_with_resilience": ("lexigram.events.reactive", "retry_with_resilience"),
}


def __getattr__(name: str) -> Any:
    """Lazy load attributes to avoid circular imports."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """List available attributes for IDE support."""
    return list(__all__) + list(_LAZY_IMPORTS.keys())


__all__ = list(_LAZY_IMPORTS)
