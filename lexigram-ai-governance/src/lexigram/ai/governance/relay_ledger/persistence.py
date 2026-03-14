"""SQL persistence for the relay ledger (top-ups and check-ins).

Only generic ``execute``/``execute_query`` SQL is used so the store
works on any backend.  Idempotency is enforced by the schema: top-up
settlement is compare-and-set on ``status``, and check-ins are
PK-guarded on ``(user_id, day)`` so a second same-day award can never
be written.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.ai.relay import (
    RelayCheckinRecord,
    RelayTopUpRecord,
)

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

__all__ = ["SqlRelayLedgerStore"]

_CREATE_TOPUPS = """
CREATE TABLE IF NOT EXISTS ai_relay_topups (
    reference_id  TEXT NOT NULL PRIMARY KEY,
    user_id       TEXT NOT NULL,
    amount        TEXT NOT NULL,
    status        TEXT NOT NULL,
    created_at    TEXT NOT NULL
)
"""

_CREATE_CHECKINS = """
CREATE TABLE IF NOT EXISTS ai_relay_checkins (
    user_id     TEXT NOT NULL,
    day         TEXT NOT NULL,
    award       TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    PRIMARY KEY (user_id, day)
)
"""

_INSERT_TOPUP = (
    "INSERT INTO ai_relay_topups "
    "(reference_id, user_id, amount, status, created_at) "
    "VALUES (?, ?, ?, ?, ?)"
)

_INSERT_CHECKIN = (
    "INSERT OR IGNORE INTO ai_relay_checkins "
    "(user_id, day, award, created_at) VALUES (?, ?, ?, ?)"
)

_SETTLE_TOPUP = (
    "UPDATE ai_relay_topups SET status = 'completed' "
    "WHERE reference_id = ? AND status = ?"
)

_SELECT_TOPUP = "SELECT status FROM ai_relay_topups WHERE reference_id = ?"

_LIST_TOPUPS = (
    "SELECT reference_id, user_id, amount, status, created_at "
    "FROM ai_relay_topups WHERE user_id = ? "
    "ORDER BY created_at DESC, rowid DESC LIMIT ?"
)


def _row_to_topup(row: dict[str, Any]) -> RelayTopUpRecord:
    """Rebuild a top-up record from a stored row."""
    return RelayTopUpRecord(
        reference_id=row["reference_id"],
        user_id=row["user_id"],
        amount=row["amount"],
        status=row["status"],
        created_at=row["created_at"],
    )


class SqlRelayLedgerStore:
    """SQL-backed ledger rows for top-ups and daily check-ins.

    Creates both ledger tables lazily on first use.  Callers are the
    :class:`~lexigram.ai.governance.relay_ledger.ledger.RelayLedgerService`,
    the only permitted mutation path.

    Args:
        db: A connected
            :class:`~lexigram.contracts.data.DatabaseProviderProtocol`
            resolved from the DI container.
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        self._db = db
        self._initialised = False

    async def _ensure_tables(self) -> None:
        """Create the ledger schema once, on first use."""
        if not self._initialised:
            await self._db.execute(_CREATE_TOPUPS)
            await self._db.execute(_CREATE_CHECKINS)
            self._initialised = True

    async def insert_topup(self, record: RelayTopUpRecord) -> None:
        """Insert one top-up row."""
        await self._ensure_tables()
        await self._db.execute(
            _INSERT_TOPUP,
            [
                record.reference_id,
                record.user_id,
                record.amount,
                record.status,
                record.created_at,
            ],
        )

    async def settle_topup(self, reference_id: str, expected_status: str) -> bool:
        """Flip *reference_id* from *expected_status* to completed.

        Returns:
            ``True`` when exactly one row flipped, ``False`` otherwise.
        """
        await self._ensure_tables()
        result = await self._db.execute(_SETTLE_TOPUP, [reference_id, expected_status])
        return result.row_count > 0

    async def topup_status(self, reference_id: str) -> str | None:
        """Return the current status of *reference_id*, or ``None``."""
        await self._ensure_tables()
        result = await self._db.execute_query(_SELECT_TOPUP, [reference_id])
        if not result.rows:
            return None
        return result.rows[0]["status"]

    async def insert_checkin(self, record: RelayCheckinRecord) -> bool:
        """Insert one check-in row, PK-guarded on ``(user_id, day)``.

        Returns:
            ``True`` when the award was written, ``False`` when the
            user already checked in that day.
        """
        await self._ensure_tables()
        result = await self._db.execute(
            _INSERT_CHECKIN,
            [record.user_id, record.day, record.award, record.created_at],
        )
        return result.row_count > 0

    async def list_topups(self, user_id: str, limit: int) -> list[RelayTopUpRecord]:
        """Return *user_id* top-ups, newest first, capped at *limit*."""
        await self._ensure_tables()
        result = await self._db.execute_query(_LIST_TOPUPS, [user_id, limit])
        return [_row_to_topup(row) for row in result.rows]
