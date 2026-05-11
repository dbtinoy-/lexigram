"""Database bridge event store that uses lexigram-sql's DatabaseProvider."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.events.stores.base import AbstractEventStore, StoredEvent

if TYPE_CHECKING:
    from lexigram.contracts import DatabaseProviderProtocol
    from lexigram.events.messages.event import Event


class DatabaseBridgeEventStore(AbstractEventStore):
    """Event store that uses lexigram-sql's DatabaseProvider for connections.

    Benefits:
    - Shares connection pool with the main application
    - Participates in DatabaseProvider health monitoring
    - Uses the same connection configuration (one source of truth)
    - Supports all backends that lexigram-sql supports
    """

    def __init__(
        self,
        db_provider: DatabaseProviderProtocol,
        events_table: str = "domain_events",
        auto_create_tables: bool = True,
    ):
        self._db = db_provider
        self._events_table = events_table
        self._auto_create = auto_create_tables

    async def append(
        self,
        stream_id: str,
        events: list[Event],
        expected_version: int | None = None,
    ) -> int:
        """Append events to a stream."""
        from lexigram import serialization as json

        conn = await self._db.acquire()
        try:
            for event in events:
                event_data = (
                    event.model_dump() if hasattr(event, "model_dump") else dict(event)  # type: ignore[call-overload]
                )
                await conn.execute(
                    f"""INSERT INTO {self._events_table} 
                    (stream_id, stream_version, event_type, event_data, metadata, timestamp)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    """,
                    stream_id,
                    expected_version or 1,
                    event_data.get("event_type", event.__class__.__name__),
                    json.dumps(event_data),
                    json.dumps(event_data.get("metadata", {})),
                )
            return expected_version or 1
        finally:
            await self._db.release(conn)

    async def read(
        self,
        stream_id: str,
        from_version: int = 0,
        to_version: int | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        """Read events from a stream as standard Event objects."""
        from lexigram import serialization as json
        from lexigram.events.messages.event import Event as EventCls

        conn = await self._db.acquire()
        try:
            query = f"SELECT * FROM {self._events_table} WHERE stream_id = $1"
            params: list[Any] = [stream_id]

            if from_version:
                query += f" AND stream_version >= ${len(params) + 1}"
                params.append(from_version)
            if to_version is not None:
                query += f" AND stream_version <= ${len(params) + 1}"
                params.append(to_version)
            if limit is not None:
                query += f" LIMIT ${len(params) + 1}"
                params.append(limit)

            query += " ORDER BY stream_version ASC"

            rows = await conn.fetch(query, *params)

            events: list[Event] = []
            for row in rows:
                raw = (
                    json.loads(row["event_data"])
                    if isinstance(row["event_data"], str)
                    else dict(row["event_data"])
                )
                # Merge top-level DB columns into the data dict for reconstruction
                raw.setdefault("event_type", row["event_type"])
                raw.setdefault("aggregate_id", row["stream_id"])
                raw.setdefault("sequence_number", row["stream_version"])
                events.append(EventCls(**raw))

            return events
        finally:
            await self._db.release(conn)

    async def read_all(  # type: ignore[override]
        self,
        position: int = 0,
        count: int | None = None,
    ) -> list[StoredEvent]:
        """Read all events from the store."""
        from lexigram import serialization as json

        conn = await self._db.acquire()
        try:
            query = f"SELECT * FROM {self._events_table} ORDER BY global_sequence ASC"
            params: list[Any] = []
            if count is not None:
                query += f" LIMIT ${len(params) + 1}"
                params.append(count)
            query += f" OFFSET ${len(params) + 1}"
            params.append(position)

            rows = await conn.fetch(query, *params)

            return [
                StoredEvent(
                    global_sequence=row["global_sequence"],
                    stream_id=row["stream_id"],
                    stream_version=row["stream_version"],
                    event_id=row.get("event_id") or row["id"],
                    event_type=row["event_type"],
                    event_data=json.loads(row["event_data"]),
                    metadata=json.loads(row["metadata"])
                    if row.get("metadata")
                    else None,
                    timestamp=row["timestamp"],
                )
                for row in rows
            ]
        finally:
            await self._db.release(conn)

    async def get_stream_info(self, stream_id: str) -> dict[str, Any] | None:  # type: ignore[override]
        """Get information about a stream."""
        conn = await self._db.acquire()
        try:
            row = await conn.fetchrow(
                f"SELECT COUNT(*) as count, MAX(stream_version) as version FROM {self._events_table} WHERE stream_id = $1",
                stream_id,
            )
            if row:
                return {
                    "stream_id": stream_id,
                    "event_count": row["count"],
                    "version": row["version"],
                }
            return None
        finally:
            await self._db.release(conn)

    async def delete_stream(self, stream_id: str) -> bool:
        """Delete all events for a stream."""
        conn = await self._db.acquire()
        try:
            result = await conn.execute(
                f"DELETE FROM {self._events_table} WHERE stream_id = $1",
                stream_id,
            )
            return str(result) != "DELETE 0"
        finally:
            await self._db.release(conn)


__all__ = ["DatabaseBridgeEventStore"]
