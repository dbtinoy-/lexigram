"""Test-friendly aliases for in-memory fakes from lexigram.testing.memory.

Re-exports all ``InMemory*`` implementations under shorter ``Fake*`` names
that read naturally in test code.

Example::

    from lexigram.testing.testkit.fakes import FakeEventBus, FakeRepository

    event_bus = FakeEventBus()
    repo: FakeRepository[User] = FakeRepository()
"""

from __future__ import annotations

from lexigram.testing.memory.audit import InMemoryAuditLogger as FakeAuditLogger
from lexigram.testing.memory.cqrs import InMemoryCommandBus as FakeCommandBus
from lexigram.testing.memory.cqrs import InMemoryQueryBus as FakeQueryBus
from lexigram.testing.memory.event_bus import InMemoryEventBus as FakeEventBus
from lexigram.testing.memory.lock import InMemoryDistributedLock as FakeLock
from lexigram.testing.memory.outbox import InMemoryOutbox as FakeOutbox
from lexigram.testing.memory.repository import InMemoryRepository as FakeRepository
from lexigram.testing.memory.uow import InMemoryUnitOfWork as FakeUoW

__all__ = [
    "FakeAuditLogger",
    "FakeCommandBus",
    "FakeEventBus",
    "FakeLock",
    "FakeOutbox",
    "FakeQueryBus",
    "FakeRepository",
    "FakeUoW",
]
