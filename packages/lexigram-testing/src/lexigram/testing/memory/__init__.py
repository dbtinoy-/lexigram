"""In-memory implementations for Lexigram Framework testing.

Provides in-memory implementations of core framework contracts for use in
unit tests, integration tests, and local development. These implementations
are lightweight, fast, and require no external infrastructure.

Exports:
    InMemoryRepository: Generic in-memory data repository.
    InMemoryEventBus: Single-process event dispatch.
    InMemoryCommandBus, InMemoryQueryBus: CQRS buses.
    InMemoryUnitOfWork: Entity tracking and event collection.
    InMemoryAuditLogger: In-memory audit logging.
    InMemoryDistributedLock: Cross-coroutine distributed lock.
    InMemoryAsyncLock: In-process asyncio mutual-exclusion lock.
    InMemoryOutbox, OutboxRelay, OutboxEntry, OutboxStatus: Outbox pattern.
    CommandBusError, CommandHandlerNotFoundError, DuplicateHandlerError,
    QueryBusError, QueryDuplicateHandlerError, QueryHandlerNotFoundError: Errors.
    MemoryProvider: DI provider for in-memory implementations.
    MemoryConfig: Configuration model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.testing.memory.audit import InMemoryAuditLogger
    from lexigram.testing.memory.blob_store import FileInfo, InMemoryBlobStore
    from lexigram.testing.memory.cache import InMemoryCacheBackend
    from lexigram.testing.memory.cqrs import (
        InMemoryCommandBus,
        InMemoryQueryBus,
    )
    from lexigram.testing.memory.event_bus import InMemoryEventBus
    from lexigram.testing.memory.exceptions import (
        CommandBusError,
        CommandError,
        CommandHandlerNotFoundError,
        DuplicateHandlerError,
        QueryBusError,
        QueryDuplicateHandlerError,
        QueryHandlerNotFoundError,
    )
    from lexigram.testing.memory.lock import (
        InMemoryAsyncLock,
        InMemoryDistributedLock,
        InMemoryLockStore,
    )
    from lexigram.testing.memory.outbox import (
        InMemoryOutbox,
        OutboxEntry,
        OutboxRelay,
        OutboxStatus,
    )
    from lexigram.testing.memory.repository import InMemoryRepository
    from lexigram.testing.memory.uow import InMemoryUnitOfWork

_LAZY_IMPORTS: dict[str, str] = {
    "InMemoryBlobStore": "lexigram.testing.memory.blob_store",
    "FileInfo": "lexigram.testing.memory.blob_store",
    "InMemoryCacheBackend": "lexigram.testing.memory.cache",
    "InMemoryAuditLogger": "lexigram.testing.memory.audit",
    "CommandBusError": "lexigram.testing.memory.exceptions",
    "CommandError": "lexigram.testing.memory.exceptions",
    "CommandHandlerNotFoundError": "lexigram.testing.memory.exceptions",
    "DuplicateHandlerError": "lexigram.testing.memory.exceptions",
    "InMemoryCommandBus": "lexigram.testing.memory.cqrs",
    "InMemoryQueryBus": "lexigram.testing.memory.cqrs",
    "QueryBusError": "lexigram.testing.memory.exceptions",
    "QueryDuplicateHandlerError": "lexigram.testing.memory.exceptions",
    "QueryHandlerNotFoundError": "lexigram.testing.memory.exceptions",
    "InMemoryEventBus": "lexigram.testing.memory.event_bus",
    "InMemoryAsyncLock": "lexigram.testing.memory.lock",
    "InMemoryDistributedLock": "lexigram.testing.memory.lock",
    "InMemoryLockStore": "lexigram.testing.memory.lock",
    "InMemoryOutbox": "lexigram.testing.memory.outbox",
    "OutboxEntry": "lexigram.testing.memory.outbox",
    "OutboxRelay": "lexigram.testing.memory.outbox",
    "OutboxStatus": "lexigram.testing.memory.outbox",
    "InMemoryRepository": "lexigram.testing.memory.repository",
    "InMemoryUnitOfWork": "lexigram.testing.memory.uow",
    "MemoryConfig": "lexigram.testing.memory.config.models",
    "MemoryBackendError": "lexigram.testing.memory.exceptions",
    "MemoryProvider": "lexigram.testing.memory.di.provider",
    "DEFAULT_AUDIT_CAPACITY": "lexigram.testing.memory.constants",
    "DEFAULT_EVENT_BUS_CAPACITY": "lexigram.testing.memory.constants",
    "DEFAULT_OUTBOX_CAPACITY": "lexigram.testing.memory.constants",
    "DEFAULT_REPOSITORY_CAPACITY": "lexigram.testing.memory.constants",
}


def __getattr__(name: str) -> object:
    """Lazily import and return a public attribute by name."""
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    """Return list of public API names."""
    return list(_LAZY_IMPORTS.keys())


__all__ = list(_LAZY_IMPORTS.keys())
