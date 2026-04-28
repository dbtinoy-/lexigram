"""SQL-backed implementation of AdminEmailOtpStoreProtocol.

Owns all DDL and DML for the ``admin_email_otps`` table.  The service layer
depends only on ``AdminEmailOtpStoreProtocol`` from
``lexigram.admin.auth.protocols`` — never on this class directly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from lexigram.admin.sql_dialect import is_postgres, now_expr
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)

_TABLE = "admin_email_otps"


def _parse_dt(value: Any) -> datetime | None:
    """Parse a provider-returned timestamp into a UTC-aware datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


@inject
class AdminEmailOtpSqlStore:
    """SQL-backed store for email one-time-password codes.

    Implements ``AdminEmailOtpStoreProtocol`` via structural subtyping.
    Manages the ``admin_email_otps`` table including DDL bootstrap and
    single-use consumption semantics.
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        """Initialise with a resolved database provider.

        Args:
            db: Framework database provider exposing ``execute`` and
                ``execute_query``.
        """
        self._db = db
        self._initialized = False

    # ------------------------------------------------------------------
    # Schema bootstrap (DDL)
    # ------------------------------------------------------------------

    async def ensure_schema(self) -> None:
        """Create the OTP table if it does not exist (idempotent)."""
        if self._initialized:
            return
        if is_postgres(self._db):
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {_TABLE} (
                    id          TEXT         PRIMARY KEY,
                    user_id     TEXT         NOT NULL,
                    code_hash   VARCHAR(64)  NOT NULL,
                    expires_at  TIMESTAMPTZ  NOT NULL,
                    used_at     TIMESTAMPTZ,
                    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
                )
            """
        else:
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {_TABLE} (
                    id          TEXT         PRIMARY KEY,
                    user_id     TEXT         NOT NULL,
                    code_hash   VARCHAR(64)  NOT NULL,
                    expires_at  TIMESTAMP    NOT NULL,
                    used_at     TIMESTAMP,
                    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """
        await self._db.execute(create_sql, [])
        self._initialized = True

    # ------------------------------------------------------------------
    # AdminEmailOtpStoreProtocol
    # ------------------------------------------------------------------

    async def save(
        self, user_id: str, code_hash: str, expires_at: datetime
    ) -> None:
        """Persist a new emailed code (see protocol docs)."""
        await self._db.execute(
            f"INSERT INTO {_TABLE} (id, user_id, code_hash, expires_at) "
            "VALUES (?, ?, ?, ?)",
            [str(uuid.uuid4()), user_id, code_hash, expires_at],
        )

    async def consume(self, user_id: str, code_hash: str) -> bool:
        """Atomically consume a matching unexpired code (see protocol docs)."""
        result = await self._db.execute(
            f"""
            UPDATE {_TABLE} SET used_at = {now_expr(self._db)}
            WHERE user_id = ?
              AND code_hash = ?
              AND used_at IS NULL
              AND expires_at > {now_expr(self._db)}
            """,
            [user_id, code_hash],
        )
        row_count = getattr(result, "row_count", None)
        if row_count is not None:
            return int(row_count) > 0
        return True

    async def last_sent_at(self, user_id: str) -> datetime | None:
        """Return the creation time of the most recent code (see protocol docs)."""
        result = await self._db.execute_query(
            f"SELECT created_at FROM {_TABLE} "
            "WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            [user_id],
        )
        row = None
        if hasattr(result, "rows") and result.rows:
            row = result.rows[0]
        elif isinstance(result, list) and result:
            row = result[0]
        elif isinstance(result, dict):
            row = result
        if not row:
            return None
        return _parse_dt(row.get("created_at"))


__all__ = ["AdminEmailOtpSqlStore"]
