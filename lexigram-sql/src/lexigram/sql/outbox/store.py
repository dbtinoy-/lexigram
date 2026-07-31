"""SQL-backed outbox store for transactional event delivery."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import uuid

from lexigram.contracts.data.outbox import OutboxStoreProtocol
from lexigram.contracts.domain.events import DomainEvent
from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock
from lexigram.serialization import dumps_str as json_dumps

if TYPE_CHECKING:
    from lexigram.contracts.core.identity import IdGeneratorProtocol

logger = get_logger(__name__)


class SQLOutboxStore:
    """SQL implementation of the transactional outbox.

    Args:
        db: Database provider for query execution.
        table: Outbox table name. Defaults to ``outbox_events``.
    """

    def __init__(
        self,
        db: Any,
        table: str = "outbox_events",
        id_generator: IdGeneratorProtocol | None = None,
    ) -> None:
        self._db = db
        self._table = table
        self._id_generator = id_generator

    async def append_batch(self, events: list[DomainEvent]) -> None:
        """Write events to the outbox table inside the active transaction."""
        if not events:
            return
        for event in events:
            payload = json_dumps(event.__dict__)
            event_id = (
                str(self._id_generator.generate())
                if self._id_generator
                else str(uuid.uuid4())
            )
            created_at = ambient_clock.now().isoformat()
            await self._db.execute(
                f"INSERT INTO {self._table} (id, event_type, payload, status, created_at) "  # noqa: S608 -- self._table set at init (default "outbox_events"), values parameterized
                "VALUES (:id, :event_type, :payload, 'pending', :created_at)",
                {
                    "id": event_id,
                    "event_type": type(event).__name__,
                    "payload": payload,
                    "created_at": created_at,
                },
            )
        logger.debug("outbox_events_written", count=len(events))

    async def fetch_pending(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch undelivered outbox events ordered by creation time."""
        rows = await self._db.fetch_all(
            f"SELECT id, event_type, payload, status, created_at FROM {self._table} "  # noqa: S608 -- self._table set at init (default "outbox_events"), values parameterized
            "WHERE status = 'pending' ORDER BY created_at ASC LIMIT :limit",
            {"limit": limit},
        )
        return [dict(row) for row in rows]

    async def mark_delivered(self, event_id: str) -> None:
        """Mark an outbox event as delivered."""
        await self._db.execute(
            f"UPDATE {self._table} SET status = 'delivered' WHERE id = :id",  # noqa: S608 -- self._table set at init (default "outbox_events"), values parameterized
            {"id": event_id},
        )

    async def mark_failed(self, event_id: str, error: str = "") -> None:
        """Mark an outbox event as permanently failed."""
        await self._db.execute(
            f"UPDATE {self._table} SET status = 'failed', error = :error WHERE id = :id",  # noqa: S608 -- self._table set at init (default "outbox_events"), values parameterized
            {"id": event_id, "error": error},
        )


__all__ = ["SQLOutboxStore"]

# Verify protocol compliance at import time (fails fast if signature drifts)
_: OutboxStoreProtocol = SQLOutboxStore.__new__(SQLOutboxStore)
