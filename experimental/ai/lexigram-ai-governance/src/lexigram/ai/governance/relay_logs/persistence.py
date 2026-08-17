"""SQL-backed relay request-log store.

Persists redaction-safe dispatch entries through
:class:`~lexigram.contracts.data.DatabaseProviderProtocol` using only
generic ``execute``/``execute_query`` SQL so the store works on any
backend.  Writes are insert-only and idempotent: ``request_id`` is the
primary key and a duplicate append is ignored, so retries and
concurrent writes never double-record a dispatch.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.ai.relay import (
    RelayRequestLogEntry,
    RelayRequestLogStoreProtocol,
)

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

__all__ = ["SqlRelayRequestLogStore"]

_CREATE_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS ai_relay_request_logs (
    request_id        TEXT    NOT NULL PRIMARY KEY,
    user_id           TEXT    NOT NULL,
    token_id          TEXT    NOT NULL,
    endpoint_kind     TEXT    NOT NULL,
    model             TEXT    NOT NULL,
    channel_name      TEXT    NOT NULL DEFAULT '',
    status            TEXT    NOT NULL,
    created_at        TEXT    NOT NULL,
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    cost              TEXT    NOT NULL DEFAULT '0',
    latency_ms        INTEGER NOT NULL DEFAULT 0,
    error_code        TEXT    NOT NULL DEFAULT ''
)
"""

_CREATE_LOG_INDEX = """
CREATE INDEX IF NOT EXISTS idx_ai_relay_request_logs_scope
    ON ai_relay_request_logs (user_id, model, created_at)
"""

_INSERT_LOG = (
    "INSERT OR IGNORE INTO ai_relay_request_logs "
    "(request_id, user_id, token_id, endpoint_kind, model, channel_name, "
    "status, created_at, prompt_tokens, completion_tokens, cost, latency_ms, "
    "error_code) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


class SqlRelayRequestLogStore(RelayRequestLogStoreProtocol):
    """SQL-backed request-log sink.

    Creates the ``ai_relay_request_logs`` table lazily on first use and
    appends entries insert-only; a duplicate ``request_id`` is ignored.

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
            await self._db.execute(_CREATE_LOG_TABLE)
            await self._db.execute(_CREATE_LOG_INDEX)
            self._initialised = True

    async def append(self, entry: RelayRequestLogEntry) -> None:
        """Persist *entry*, ignoring a duplicate ``request_id``.

        Args:
            entry: The redaction-safe dispatch entry to persist.
        """
        await self._ensure_tables()
        await self._db.execute(
            _INSERT_LOG,
            [
                entry.request_id,
                entry.user_id,
                entry.token_id,
                entry.endpoint_kind,
                entry.model,
                entry.channel_name,
                entry.status,
                entry.created_at.isoformat(),
                entry.prompt_tokens,
                entry.completion_tokens,
                entry.cost,
                entry.latency_ms,
                entry.error_code,
            ],
        )
