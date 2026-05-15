"""SQL-backed durable relay channel store.

Persists channel rows through
:class:`~lexigram.contracts.data.DatabaseProviderProtocol` using only
generic ``execute``/``execute_query`` SQL so the store works on any
backend.  Every mutation is compare-and-set on ``revision``: stale
writers (a mismatched ``expected_revision``) are rejected instead of
overwriting newer state, and ``delete`` only removes the row matching
the expected revision.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.ai.relay.gateway import RelayChannel
from lexigram.contracts.ai.relay.store import (
    RelayChannelSnapshot,
    RelayChannelStoreProtocol,
)
from lexigram.contracts.ai.relay.types import RelayFormat
from lexigram.primitives import clock
from lexigram.serialization import dumps_str, loads_str

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

__all__ = ["SqlRelayChannelStore"]

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS ai_relay_channels (
    name        TEXT    NOT NULL PRIMARY KEY,
    payload     TEXT    NOT NULL,
    revision    INTEGER NOT NULL,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
)
"""

_SELECT_ROW = "SELECT revision FROM ai_relay_channels WHERE name = ?"

_SELECT_ALL = (
    "SELECT name, payload, revision, created_at, updated_at "
    "FROM ai_relay_channels ORDER BY name"
)

_INSERT_ROW = (
    "INSERT INTO ai_relay_channels "
    "(name, payload, revision, created_at, updated_at) VALUES (?, ?, 1, ?, ?)"
)

_UPDATE_ROW = (
    "UPDATE ai_relay_channels SET payload = ?, updated_at = ?, revision = ? "
    "WHERE name = ? AND revision = ?"
)

_DELETE_ROW = "DELETE FROM ai_relay_channels WHERE name = ? AND revision = ?"


def _payload(channel: RelayChannel) -> str:
    """Encode a channel as canonical JSON (sets sorted, enum values)."""
    return dumps_str(
        {
            "name": channel.name,
            "upstream_base_url": channel.upstream_base_url,
            "target_format": channel.target_format.value,
            "models": list(channel.models),
            "capabilities": sorted(channel.capabilities),
            "endpoint_kinds": sorted(channel.endpoint_kinds),
            "priority": channel.priority,
            "weight": channel.weight,
            "enabled": channel.enabled,
            "timeout_seconds": channel.timeout_seconds,
        }
    )


def _decode_channel(data: dict[str, Any]) -> RelayChannel:
    """Rebuild a ``RelayChannel`` from a canonical payload dict."""
    return RelayChannel(
        name=data["name"],
        upstream_base_url=data["upstream_base_url"],
        target_format=RelayFormat(data["target_format"]),
        models=tuple(data["models"]),
        capabilities=frozenset(data["capabilities"]),
        endpoint_kinds=frozenset(data["endpoint_kinds"]),
        priority=data["priority"],
        weight=data["weight"],
        enabled=data["enabled"],
        timeout_seconds=data["timeout_seconds"],
    )


class SqlRelayChannelStore(RelayChannelStoreProtocol):
    """SQL-backed CRUD over durable channel rows.

    Creates the ``ai_relay_channels`` table lazily on first use.
    ``upsert`` matches on ``channel.name`` and returns the new revision;
    ``delete`` returns whether a row was removed.

    Args:
        db: A connected
            :class:`~lexigram.contracts.data.DatabaseProviderProtocol`
            resolved from the DI container.
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        self._db = db
        self._initialised = False

    async def _ensure_tables(self) -> None:
        """Create the storage schema once, on first use."""
        if not self._initialised:
            await self._db.execute(_CREATE_TABLE)
            self._initialised = True

    async def list_channels(self) -> list[RelayChannelSnapshot]:
        """Return all durable channels ordered by name.

        Returns:
            One snapshot per stored channel.
        """
        await self._ensure_tables()
        result = await self._db.execute_query(_SELECT_ALL)
        return [
            RelayChannelSnapshot(
                channel=_decode_channel(loads_str(row["payload"])),
                revision=int(row["revision"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in result.rows
        ]

    async def upsert(
        self, channel: RelayChannel, *, expected_revision: int | None = None
    ) -> int | None:
        """Insert or update *channel* under compare-and-set.

        A new name inserts at revision 1 (any ``expected_revision`` on an
        absent row is treated as a stale write and rejected).  An
        existing row updates only when ``expected_revision`` matches its
        current revision, bumping the revision by one.

        Args:
            channel: The channel to persist.
            expected_revision: Revision the caller observed; ``None``
                for a blind write (on an existing name this still
                verifies against the live revision).

        Returns:
            The new revision on success, ``None`` on a stale write.
        """
        await self._ensure_tables()
        now = clock.now().isoformat()
        payload = _payload(channel)
        current = await self._db.execute_query(_SELECT_ROW, [channel.name])
        if not current.rows:
            if expected_revision is not None:
                return None
            await self._db.execute(_INSERT_ROW, [channel.name, payload, now, now])
            return 1
        revision = int(current.rows[0]["revision"])
        if expected_revision is not None and expected_revision != revision:
            return None
        new_revision = revision + 1
        updated = await self._db.execute(
            _UPDATE_ROW,
            [payload, now, new_revision, channel.name, revision],
        )
        if updated.row_count == 0:
            return None
        return new_revision

    async def delete(self, name: str, *, expected_revision: int) -> bool:
        """Delete the row for *name* under compare-and-set.

        Args:
            name: The channel name to delete.
            expected_revision: Revision the caller observed.

        Returns:
            ``True`` when a row was removed, ``False`` when the channel
            is absent or the revision is stale.
        """
        await self._ensure_tables()
        result = await self._db.execute(_DELETE_ROW, [name, expected_revision])
        return result.row_count > 0
