"""SQL-backed implementation of AdminEmailVerificationStoreProtocol.

Owns all DDL and DML for the ``admin_email_verifications`` table.  The
service layer depends only on ``AdminEmailVerificationStoreProtocol`` from
``lexigram.admin.auth.protocols`` — never on this class directly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lexigram.admin.sql_dialect import is_postgres, now_expr
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)

_TABLE = "admin_email_verifications"


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
class AdminEmailVerificationSqlStore:
    """SQL-backed store for admin email verification state.

    Implements ``AdminEmailVerificationStoreProtocol`` via structural
    subtyping.  Manages the ``admin_email_verifications`` table including
    DDL bootstrap and single-use token consumption semantics.
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
        """Create the verification table if it does not exist (idempotent)."""
        if self._initialized:
            return
        if is_postgres(self._db):
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {_TABLE} (
                    user_id          TEXT         PRIMARY KEY,
                    email_verified_at TIMESTAMPTZ,
                    token_hash       VARCHAR(64),
                    token_expires_at TIMESTAMPTZ,
                    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
                )
            """
        else:
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {_TABLE} (
                    user_id          TEXT         PRIMARY KEY,
                    email_verified_at TIMESTAMP,
                    token_hash       VARCHAR(64),
                    token_expires_at TIMESTAMP,
                    updated_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """
        await self._db.execute(create_sql, [])
        await self._db.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{_TABLE}_token
            ON {_TABLE} (token_hash)
            """,
            [],
        )
        self._initialized = True

    # ------------------------------------------------------------------
    # AdminEmailVerificationStoreProtocol
    # ------------------------------------------------------------------

    async def is_verified(self, user_id: str) -> bool:
        """Return True when the user's email is verified (see protocol docs)."""
        result = await self._db.execute_query(
            f"SELECT email_verified_at FROM {_TABLE} WHERE user_id = ?",
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
            return False
        return _parse_dt(row.get("email_verified_at")) is not None

    async def find_user_by_token_hash(self, token_hash: str) -> str | None:
        """Look up the user owning an unconsumed token (see protocol docs)."""
        result = await self._db.execute_query(
            f"SELECT user_id FROM {_TABLE} "
            "WHERE token_hash = ? AND email_verified_at IS NULL",
            [token_hash],
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
        return str(row.get("user_id", ""))

    async def save_token(
        self, user_id: str, token_hash: str, expires_at: datetime
    ) -> None:
        """Persist (or refresh) the verification token for a user."""
        await self._db.execute(
            f"""
            INSERT INTO {_TABLE} (user_id, token_hash, token_expires_at)
            VALUES (?, ?, ?)
            ON CONFLICT (user_id) DO UPDATE SET
                token_hash = excluded.token_hash,
                token_expires_at = excluded.token_expires_at,
                updated_at = {now_expr(self._db)}
            """,
            [user_id, token_hash, expires_at],
        )

    async def consume_token(self, user_id: str, token_hash: str) -> bool:
        """Atomically verify + consume a token (see protocol docs)."""
        result = await self._db.execute(
            f"""
            UPDATE {_TABLE} SET
                email_verified_at = {now_expr(self._db)},
                token_hash = NULL,
                token_expires_at = NULL,
                updated_at = {now_expr(self._db)}
            WHERE user_id = ?
              AND token_hash = ?
              AND email_verified_at IS NULL
              AND token_expires_at > {now_expr(self._db)}
            """,
            [user_id, token_hash],
        )
        row_count = getattr(result, "row_count", None)
        if row_count is not None:
            return int(row_count) > 0
        return True

    async def clear_token(self, user_id: str) -> None:
        """Remove the pending verification token for a user."""
        await self._db.execute(
            f"""
            UPDATE {_TABLE} SET
                token_hash = NULL,
                token_expires_at = NULL,
                updated_at = {now_expr(self._db)}
            WHERE user_id = ?
            """,
            [user_id],
        )


__all__ = ["AdminEmailVerificationSqlStore"]
