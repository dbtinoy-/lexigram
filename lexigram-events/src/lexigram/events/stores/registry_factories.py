from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.core.container import (  # type: ignore[import-untyped]
        ContainerResolverProtocol,
    )
    from lexigram.events.config import EventsConfig
    from lexigram.events.stores.base import AbstractEventStore


def create_inmemory_store(
    config: EventsConfig,
    container: ContainerResolverProtocol,
) -> AbstractEventStore:
    """Create an in-memory event store."""
    from lexigram.events.stores.memory import InMemoryEventStore

    return InMemoryEventStore(  # type: ignore[abstract]
        max_events_per_stream=config.memory.max_events_per_stream,
    )


def create_postgres_store(
    config: EventsConfig,
    container: ContainerResolverProtocol,
) -> AbstractEventStore:
    """Create a PostgreSQL event store using the injected DB provider."""
    from lexigram.contracts.data.sql.database import DatabaseProviderProtocol
    from lexigram.events.stores.postgres.event_store import PostgresEventStore

    provider = container.resolve_sync(DatabaseProviderProtocol)
    pg_config = config.postgres
    if pg_config is None:
        raise ValueError("PostgreSQL backend selected but postgres config is missing")
    return PostgresEventStore(config=pg_config, provider=provider)  # type: ignore[abstract]


def create_mongodb_store(
    config: EventsConfig,
    container: ContainerResolverProtocol,
) -> AbstractEventStore:
    """Create a MongoDB event store."""
    from lexigram.contracts.data import DocumentStoreProtocol
    from lexigram.events.stores.mongodb.event_store import MongoDBEventStore

    mongo_config = config.mongodb
    if mongo_config is None:
        raise ValueError("MongoDB backend selected but mongodb config is missing")
    document_store = container.resolve_sync(DocumentStoreProtocol)
    return MongoDBEventStore(document_store=document_store, config=mongo_config)  # type: ignore[abstract]


def create_sqlite_store(
    config: EventsConfig,
    container: ContainerResolverProtocol,
) -> AbstractEventStore:
    """Create a SQLite event store.

    Note: SQLite support is not yet fully integrated into EventsConfig.
    Raises NotImplementedError until sqlite config field is added.
    """
    raise NotImplementedError(
        "SQLite backend support is not yet fully integrated. "
        "Awaiting sqlite config field in EventsConfig."
    )
