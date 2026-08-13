"""Abstract Unit of Work base class.

Provides the full Unit-of-Work implementation.  Concrete subclasses only
need to override :meth:`_flush` to persist tracked changes (e.g. writing
to a database).  The in-memory implementation in ``lexigram.memory`` uses
the default no-op; production backends override to flush to SQL/NoSQL stores.
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any, Self

from lexigram.contracts.data.outbox import OutboxStoreProtocol
from lexigram.contracts.data.sql.unit_of_work import UnitOfWorkProtocol
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.domain.events import DomainEvent
    from lexigram.contracts.events import EventBusProtocol

logger = get_logger(__name__)


class AbstractUnitOfWork(UnitOfWorkProtocol):
    """Full Unit of Work implementation with pluggable flush semantics.

    Tracks entity changes (:meth:`register_new`, :meth:`register_dirty`,
    :meth:`register_deleted`) and domain events (:meth:`register_event`).
    On :meth:`commit`, outstanding changes are flushed via :meth:`_flush`,
    collected events are published via the optional ``event_bus``, and all
    tracking state is reset.  :meth:`rollback` discards state without
    flushing.

    Subclasses must override :meth:`_flush` to persist tracked changes to
    their storage backend.

    Args:
        event_bus: Optional event bus for publishing domain events on commit.

    Example::

        class SQLUnitOfWork(AbstractUnitOfWork):
            async def _flush(self) -> None:
                await self._session.flush()

        async with SQLUnitOfWork(event_bus=bus) as uow:
            uow.register_new(user)
            await uow.commit()
    """

    def __init__(
        self,
        event_bus: EventBusProtocol | None = None,
        outbox_store: OutboxStoreProtocol | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._outbox_store = outbox_store
        self._new: list[Any] = []
        self._dirty: list[Any] = []
        self._deleted: list[Any] = []
        self._events: list[DomainEvent] = []
        self._committed = False

    # ------------------------------------------------------------------
    # Entity tracking
    # ------------------------------------------------------------------

    def register_new(self, entity: Any) -> None:
        """Track *entity* as newly created (to be inserted).

        Args:
            entity: The entity to mark as new.
        """
        self._new.append(entity)

    def register_dirty(self, entity: Any) -> None:
        """Track *entity* as modified in this unit of work.

        Args:
            entity: The entity to mark as dirty.
        """
        self._dirty.append(entity)

    def register_deleted(self, entity: Any) -> None:
        """Track *entity* as removed from this unit of work.

        Args:
            entity: The entity to mark as deleted.
        """
        self._deleted.append(entity)

    # ------------------------------------------------------------------
    # Event collection
    # ------------------------------------------------------------------

    def register_event(self, event: DomainEvent) -> None:
        """Collect a domain event to be published on :meth:`commit`.

        Args:
            event: The domain event to buffer.
        """
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        """Return all collected events and those pulled from aggregate roots.

        Entities that expose a ``pull_events()`` method (e.g. aggregate roots)
        are harvested automatically.  The internal event list is **not** cleared
        here; it is cleared by :meth:`_clear` at the end of :meth:`commit` or
        :meth:`rollback`.

        Returns:
            All pending domain events.
        """
        events = list(self._events)
        for entity in (*self._new, *self._dirty):
            if hasattr(entity, "pull_events"):
                events.extend(entity.pull_events())
        return events

    # ------------------------------------------------------------------
    # Commit / Rollback
    # ------------------------------------------------------------------

    async def commit(self) -> None:
        """Flush tracked changes and write domain events atomically to the outbox.

        If an outbox store is configured, events are written inside the same
        transaction as the business data (via :meth:`_flush`), eliminating the
        crash window between DB commit and event publish.  When no outbox store
        is present the legacy in-process publish path is used as a fallback.
        """
        events = self.collect_events()
        await self._flush()
        if events and self._outbox_store is not None:
            await self._outbox_store.append_batch(events)
        elif events:
            await self._publish_events(events)
        self._clear()
        self._committed = True
        logger.debug(
            "uow_committed",
            new=len(self._new),
            dirty=len(self._dirty),
            deleted=len(self._deleted),
            events=len(events),
        )

    async def rollback(self) -> None:
        """Discard all tracked changes and events without flushing."""
        count = len(self._new) + len(self._dirty) + len(self._deleted)
        self._clear()
        logger.debug("uow_rolled_back", discarded_entities=count)

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> Self:
        """Begin unit of work scope."""
        self._committed = False
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Commit on success, roll back on exception."""
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()

    # ------------------------------------------------------------------
    # Extension point
    # ------------------------------------------------------------------

    @abc.abstractmethod
    async def _flush(self) -> None:
        """Persist all tracked entity changes to the backing store.

        The in-memory implementation is a no-op.  Database backends override
        this to flush to SQL/NoSQL storage.
        """

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _publish_events(self, events: list[DomainEvent]) -> None:
        """Publish *events* via the configured event bus (if any).

        Args:
            events: Domain events to dispatch.
        """
        if self._event_bus is None:
            return
        for event in events:
            await self._event_bus.publish(event)

    def _clear(self) -> None:
        """Reset all entity-tracking and event-collection state."""
        self._new.clear()
        self._dirty.clear()
        self._deleted.clear()
        self._events.clear()


__all__ = ["AbstractUnitOfWork"]
