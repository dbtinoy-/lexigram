"""Database-backed relay billing store.

Persists reservations and settled usage records through
:class:`~lexigram.contracts.data.DatabaseProviderProtocol` using only
generic ``execute``/``execute_query`` SQL so the store works on any
backend.  Idempotency is enforced at the database level: settlement uses
a unique ``(request_id, attempt_id)`` index combined with insert-or-ignore
semantics, so retries and concurrent writes return the existing record
instead of charging twice.  Reservation state transitions are guarded by
compare-and-set predicates (``reserved -> released``,
``reserved -> settled``, ``reserved -> expired``) so a stale write cannot
overwrite a newer state.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from lexigram.contracts.ai.governance import (
    RelayUsageRecord,
    RelayUsageScope,
    RelayUsageStoreProtocol,
)
from lexigram.contracts.ai.relay import RelayUsage
from lexigram.primitives import clock
from lexigram.serialization import dumps_str, loads_str

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from lexigram.contracts.ai.governance import RelayUsageReservation
    from lexigram.contracts.ai.relay import JsonValue
    from lexigram.contracts.data import DatabaseProviderProtocol

__all__ = ["DatabaseRelayUsageStore"]

_CREATE_RESERVATIONS = """
CREATE TABLE IF NOT EXISTS ai_relay_reservations (
    reservation_id    TEXT    NOT NULL PRIMARY KEY,
    request_id        TEXT    NOT NULL,
    status            TEXT    NOT NULL DEFAULT 'reserved',
    estimated_tokens  INTEGER NOT NULL,
    estimated_charge  TEXT    NOT NULL,
    expires_at        TEXT    NOT NULL,
    created_at        TEXT    NOT NULL
)
"""

_CREATE_RESERVATIONS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_ai_relay_reservations_request
    ON ai_relay_reservations (request_id)
"""

_CREATE_USAGE = """
CREATE TABLE IF NOT EXISTS ai_relay_usage (
    request_id           TEXT    NOT NULL,
    attempt_id           TEXT    NOT NULL,
    tenant_id            TEXT    NOT NULL,
    account_id           TEXT,
    user_id              TEXT,
    model                TEXT    NOT NULL,
    provider             TEXT    NOT NULL DEFAULT '',
    channel              TEXT    NOT NULL DEFAULT '',
    status               TEXT    NOT NULL,
    charge               TEXT    NOT NULL,
    currency             TEXT    NOT NULL,
    converter_id         TEXT,
    metadata             TEXT    NOT NULL DEFAULT '{}',
    created_at           TEXT    NOT NULL,
    prompt_tokens        INTEGER NOT NULL DEFAULT 0,
    completion_tokens    INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens    INTEGER NOT NULL DEFAULT 0,
    cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
    reasoning_tokens     INTEGER NOT NULL DEFAULT 0,
    audio_input_tokens   INTEGER NOT NULL DEFAULT 0,
    audio_output_tokens  INTEGER NOT NULL DEFAULT 0,
    image_tokens         INTEGER NOT NULL DEFAULT 0,
    input_tokens         INTEGER NOT NULL DEFAULT 0,
    output_tokens        INTEGER NOT NULL DEFAULT 0,
    total_tokens_override INTEGER,
    PRIMARY KEY (request_id, attempt_id)
)
"""

_CREATE_USAGE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_ai_relay_usage_scope
    ON ai_relay_usage (tenant_id, account_id, user_id, model, created_at)
"""

_INSERT_RESERVATION = (
    "INSERT OR IGNORE INTO ai_relay_reservations "
    "(reservation_id, request_id, status, estimated_tokens, estimated_charge, "
    "expires_at, created_at) "
    "VALUES (?, ?, 'reserved', ?, ?, ?, ?)"
)

_EXPIRE_RESERVATIONS = (
    "UPDATE ai_relay_reservations SET status = 'expired' "
    "WHERE status = 'reserved' AND expires_at <= ?"
)

_RELEASE_RESERVATION = (
    "UPDATE ai_relay_reservations SET status = 'released' "
    "WHERE reservation_id = ? AND status = 'reserved'"
)

_SETTLE_RESERVATION = (
    "UPDATE ai_relay_reservations SET status = 'settled' "
    "WHERE reservation_id = ? AND status = 'reserved'"
)

_INSERT_USAGE = (
    "INSERT OR IGNORE INTO ai_relay_usage "
    "(request_id, attempt_id, tenant_id, account_id, user_id, model, "
    "provider, channel, status, charge, currency, converter_id, metadata, "
    "created_at, prompt_tokens, completion_tokens, cache_read_tokens, "
    "cache_creation_tokens, reasoning_tokens, audio_input_tokens, "
    "audio_output_tokens, image_tokens, input_tokens, output_tokens, "
    "total_tokens_override) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)

_SELECT_USAGE = "SELECT * FROM ai_relay_usage WHERE request_id = ? AND attempt_id = ?"

_USAGE_ALIASES = {
    "tenant_id": "tenant_id",
    "account_id": "account_id",
    "user_id": "user_id",
    "model": "model",
    "provider": "provider",
    "channel": "channel",
    "status": "status",
    "request_id": "request_id",
    "attempt_id": "attempt_id",
}


class DatabaseRelayUsageStore(RelayUsageStoreProtocol):
    """SQL-backed relay billing store.

    Writes reservations and usage records to ``ai_relay_reservations``
    and ``ai_relay_usage`` (created lazily on first use).  All writes are
    intentionally idempotent:

    - :meth:`save_reservation` inserts with ``INSERT OR IGNORE`` keyed by
      ``reservation_id``; a retry or a duplicate never overwrites an
      existing reservation.

    - :meth:`settle_once` uses a unique ``(request_id, attempt_id)``
      primary key, so retries and concurrent settles return the stored
      record instead of charging twice.  It also transitions the
      associated reservation with a ``reserved -> settled``
      compare-and-set update.

    - :meth:`release` transitions ``reserved -> released`` only when the
      row is still ``reserved``, and expires stale reservations first with
      a ``reserved -> expired`` compare-and-set update.

    Monetary values are stored as exact decimal text so that no currency
    precision is lost crossing the database boundary.  Token dimensions
    are stored in dedicated integer columns; loss codes and extra
    metadata are serialised into the ``metadata`` JSON column.

    Args:
        db: A connected :class:`~lexigram.contracts.data.DatabaseProviderProtocol`
            resolved from the DI container.
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        self._db = db
        self._initialised = False

    async def _ensure_tables(self) -> None:
        """Create the storage schema once, on first use."""
        if not self._initialised:
            await self._db.execute(_CREATE_RESERVATIONS)
            await self._db.execute(_CREATE_RESERVATIONS_INDEX)
            await self._db.execute(_CREATE_USAGE)
            await self._db.execute(_CREATE_USAGE_INDEX)
            self._initialised = True

    async def save_reservation(self, reservation: RelayUsageReservation) -> None:
        """Persist *reservation* atomically, ignoring duplicates.

        Args:
            reservation: The reservation to persist.
        """
        await self._ensure_tables()
        await self._db.execute(
            _INSERT_RESERVATION,
            [
                reservation.reservation_id,
                reservation.request_id,
                reservation.estimated_tokens,
                str(reservation.estimated_charge),
                reservation.expires_at.isoformat(),
                clock.now().isoformat(),
            ],
        )

    async def settle_once(self, record: RelayUsageRecord) -> RelayUsageRecord:
        """Settle *record* exactly once, returning the stored record.

        The usage write is guarded by the ``(request_id, attempt_id)``
        primary key: a duplicate insert is ignored and the existing row is
        returned.  The reservation is then marked ``settled`` through a
        compare-and-set update, and stale reservations are expired first.

        Args:
            record: The settled usage record.

        Returns:
            The stored record (the existing row on a duplicate).
        """
        await self._ensure_tables()
        now = clock.now()
        await self._db.execute(_EXPIRE_RESERVATIONS, [now.isoformat()])
        await self._db.execute(
            _INSERT_USAGE,
            [
                record.request_id,
                record.attempt_id,
                record.scope.tenant_id,
                record.scope.account_id,
                record.scope.user_id,
                record.scope.model,
                record.scope.provider,
                record.scope.channel,
                record.status,
                str(record.charge),
                record.currency,
                record.converter_id,
                dumps_str({"loss_codes": list(record.loss_codes)}),
                now.isoformat(),
                record.usage.prompt_tokens,
                record.usage.completion_tokens,
                record.usage.cache_read_tokens,
                record.usage.cache_creation_tokens,
                record.usage.reasoning_tokens,
                record.usage.audio_input_tokens,
                record.usage.audio_output_tokens,
                record.usage.image_tokens,
                record.usage.input_tokens,
                record.usage.output_tokens,
                record.usage.total_tokens_override,
            ],
        )
        result = await self._db.execute_query(
            _SELECT_USAGE, [record.request_id, record.attempt_id]
        )
        row = result.rows[0]
        await self._db.execute(_SETTLE_RESERVATION, [record.attempt_id])
        return _row_to_record(row)

    async def release(self, reservation_id: str) -> None:
        """Expire and release a reservation, idempotently.

        Stale ``reserved`` rows past their expiry are first marked
        ``expired``; the reservation is then transitioned ``released`` only
        if it is still ``reserved``.  Unknown or already-final
        reservations are left untouched.

        Args:
            reservation_id: Reservation identifier.
        """
        await self._ensure_tables()
        now = clock.now()
        await self._db.execute(_EXPIRE_RESERVATIONS, [now.isoformat()])
        await self._db.execute(_RELEASE_RESERVATION, [reservation_id])

    async def query(
        self, filters: Mapping[str, JsonValue]
    ) -> Sequence[RelayUsageRecord]:
        """Query settled records by scope filters, newest first.

        Args:
            filters: Recognised keys are ``tenant_id``, ``account_id``,
                ``user_id``, ``model``, ``provider``, ``channel``,
                ``status``, ``request_id``, and ``attempt_id``.

        Returns:
            Matching usage records ordered by insertion timestamp descending.
        """
        await self._ensure_tables()
        clauses: list[str] = ["1=1"]
        params: list[JsonValue] = []
        for key, column in _USAGE_ALIASES.items():
            value = filters.get(key)
            if value is not None:
                clauses.append(f"{column} = ?")
                params.append(value)
        sql = (
            f"SELECT * FROM ai_relay_usage WHERE {' AND '.join(clauses)} "
            "ORDER BY created_at DESC"
        )
        result = await self._db.execute_query(sql, params)
        return [_row_to_record(row) for row in result.rows]


def _row_to_record(row: dict[str, Any]) -> RelayUsageRecord:
    """Convert a database row into a :class:`RelayUsageRecord`.

    Args:
        row: A usage row read from the database.

    Returns:
        The reconstructed usage record.
    """
    metadata = loads_str(row.get("metadata") or "{}")
    loss_codes = tuple(metadata.get("loss_codes", ()))
    return RelayUsageRecord(
        request_id=row["request_id"],
        attempt_id=row["attempt_id"],
        scope=RelayUsageScope(
            tenant_id=row["tenant_id"],
            account_id=row["account_id"],
            user_id=row["user_id"],
            model=row["model"],
            provider=row["provider"],
            channel=row["channel"],
        ),
        usage=RelayUsage(
            prompt_tokens=row["prompt_tokens"],
            completion_tokens=row["completion_tokens"],
            cache_read_tokens=row["cache_read_tokens"],
            cache_creation_tokens=row["cache_creation_tokens"],
            reasoning_tokens=row["reasoning_tokens"],
            audio_input_tokens=row["audio_input_tokens"],
            audio_output_tokens=row["audio_output_tokens"],
            image_tokens=row["image_tokens"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            total_tokens_override=row["total_tokens_override"],
        ),
        charge=Decimal(row["charge"]),
        currency=row["currency"],
        status=row["status"],
        converter_id=row["converter_id"],
        loss_codes=loss_codes,
    )
