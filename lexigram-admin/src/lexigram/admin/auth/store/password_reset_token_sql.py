"""SQL-backed implementation of AdminPasswordResetTokenStoreProtocol.

Owns all DDL and DML for the ``admin_password_reset_tokens`` table.  The
service layer depends only on ``AdminPasswordResetTokenStoreProtocol`` from
``lexigram.admin.auth.protocols`` — never on this class directly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lexigram.admin.auth.types import AdminPasswordResetToken
from lexigram.admin.sql_dialect import is_postgres, now_expr
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)

_TABLE = "admin_password_reset_tokens"


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
class AdminPasswordResetTokenSqlStore:
    """SQL-backed store for password reset tokens.

    Implements ``AdminPasswordResetTokenStoreProtocol`` via structural
    subtyping.  Manages the ``admin_password_reset_tokens`` table including
    DDL bootstrap and single-use consumption semantics.
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
        """Create the token table if it does not exist (idempotent)."""
        if self._initialized:
            return
        if is_postgres(self._db):
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {_TABLE} (
                    token_hash  VARCHAR(64)  PRIMARY KEY,
                    email       VARCHAR(255) NOT NULL,
                    expires_at  TIMESTAMPTZ  NOT NULL,
                    consumed_at TIMESTAMPTZ,
                    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
                )
            """
        else:
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {_TABLE} (
                    token_hash  VARCHAR(64)  PRIMARY KEY,
                    email       VARCHAR(255) NOT NULL,
                    expires_at  TIMESTAMP    NOT NULL,
                    consumed_at TIMESTAMP,
                    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """
        await self._db.execute(create_sql, [])
        self._initialized = True

    # ------------------------------------------------------------------
    # AdminPasswordResetTokenStoreProtocol
    # ------------------------------------------------------------------

    async def create(self, email: str, token_hash: str, expires_at: datetime) -> None:
        """Persist a new token record (see protocol docs)."""
        await self._db.execute(
            f"INSERT INTO {_TABLE} (token_hash, email, expires_at) VALUES (?, ?, ?)",  # noqa: S608 — table name is module constant "admin_password_reset_tokens", never user input
            [token_hash, email, expires_at],
        )

    async def find_by_hash(self, token_hash: str) -> AdminPasswordResetToken | None:
        """Look up a token by sha256 hash (see protocol docs)."""
        result = await self._db.execute_query(
            f"SELECT token_hash, email, expires_at, consumed_at FROM {_TABLE} WHERE token_hash = ?",  # noqa: S608 — table name is module constant "admin_password_reset_tokens", never user input
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
        return AdminPasswordResetToken(
            email=str(row.get("email", "")),
            token_hash=str(row.get("token_hash", token_hash)),
            expires_at=_parse_dt(row.get("expires_at")) or datetime.now(UTC),
            consumed_at=_parse_dt(row.get("consumed_at")),
        )

    async def mark_consumed(self, token_hash: str) -> bool:
        """Atomically verify-and-consume a token in one statement.

        Returns False when the token is missing, already consumed, or
        expired — the caller cannot distinguish which without a separate
        lookup.
        """
        result = await self._db.execute(
            f"UPDATE {_TABLE} SET consumed_at = {now_expr(self._db)} "  # noqa: S608 — table name is module constant, now_expr yields fixed NOW()/CURRENT_TIMESTAMP
            "WHERE token_hash = ? AND consumed_at IS NULL "
            f"AND expires_at > {now_expr(self._db)}",
            [token_hash],
        )
        row_count = getattr(result, "row_count", None)
        if row_count is not None:
            return int(row_count) > 0
        return True


__all__ = ["AdminPasswordResetTokenSqlStore"]
