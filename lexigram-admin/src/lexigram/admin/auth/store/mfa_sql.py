"""SQL-backed implementation of AdminMfaStoreProtocol.

Owns all DDL and DML for the ``admin_mfa_totp`` table.  The service
layer depends only on ``AdminMfaStoreProtocol`` from
``lexigram.admin.auth.protocols`` — never on this class directly.
"""

from __future__ import annotations

from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)

_TABLE = "admin_mfa_totp"


@inject
class AdminMfaSqlStore:
    """SQL-backed store for per-user TOTP secrets.

    Implements ``AdminMfaStoreProtocol`` via structural subtyping.
    Manages the ``admin_mfa_totp`` table including DDL bootstrap and
    idempotent enable/disable semantics.  A row's existence means 2FA
    is enabled for that user; disabling deletes the row.
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
        """Create the MFA table if it does not exist (idempotent)."""
        if self._initialized:
            return
        await self._db.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_TABLE} (
                user_id    TEXT         PRIMARY KEY,
                secret     VARCHAR(64)  NOT NULL,
                enabled_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            )
            """,
            [],
        )
        self._initialized = True

    # ------------------------------------------------------------------
    # AdminMfaStoreProtocol
    # ------------------------------------------------------------------

    async def is_enabled(self, user_id: str) -> bool:
        """Return True when the user has a stored TOTP secret."""
        return await self.get_secret(user_id) is not None

    async def get_secret(self, user_id: str) -> str | None:
        """Return the stored TOTP secret for a user (None when disabled)."""
        result = await self._db.execute_query(
            f"SELECT secret FROM {_TABLE} WHERE user_id = ?",
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
        return str(row.get("secret", ""))

    async def save_secret(self, user_id: str, secret: str) -> None:
        """Persist (or refresh) the TOTP secret for a user."""
        await self._db.execute(
            f"""
            INSERT INTO {_TABLE} (user_id, secret)
            VALUES (?, ?)
            ON CONFLICT (user_id) DO UPDATE SET
                secret = excluded.secret,
                updated_at = NOW()
            """,
            [user_id, secret],
        )

    async def disable(self, user_id: str) -> None:
        """Remove the TOTP secret for a user (2FA off)."""
        await self._db.execute(
            f"DELETE FROM {_TABLE} WHERE user_id = ?",
            [user_id],
        )


__all__ = ["AdminMfaSqlStore"]
