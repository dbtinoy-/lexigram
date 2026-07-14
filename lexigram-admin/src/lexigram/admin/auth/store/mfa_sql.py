"""SQL-backed implementation of AdminMfaStoreProtocol.

Owns all DDL and DML for the ``admin_mfa_totp`` table.  The service
layer depends only on ``AdminMfaStoreProtocol`` from
``lexigram.admin.auth.protocols`` — never on this class directly.
"""

from __future__ import annotations

from lexigram.admin.sql_dialect import is_postgres, now_expr
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.security.encryption import EncryptionService
from lexigram.security.exceptions import DecryptionError

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

    def __init__(
        self,
        db: DatabaseProviderProtocol,
        encryption_service: EncryptionService | None = None,
    ) -> None:
        """Initialise with a resolved database provider.

        Args:
            db: Framework database provider exposing ``execute`` and
                ``execute_query``.
            encryption_service: Optional AES-256-GCM service used to
                encrypt/decrypt ``secret`` at rest.  ``None`` keeps the
                legacy plaintext behavior (tests and no-crypto builds).
        """
        self._db = db
        self._encryption_service = encryption_service
        self._initialized = False

    # ------------------------------------------------------------------
    # Schema bootstrap (DDL)
    # ------------------------------------------------------------------

    async def ensure_schema(self) -> None:
        """Create the MFA table if it does not exist (idempotent).

        The ``secret`` column is ``VARCHAR(512)`` — AES-256-GCM hex
        ciphertext (nonce 12 + tag 16 + data bytes) exceeds the legacy
        ``VARCHAR(64)`` width; on Postgres an idempotent ``ALTER`` widens
        pre-existing tables.
        """
        if self._initialized:
            return
        if is_postgres(self._db):
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {_TABLE} (
                    user_id    TEXT         PRIMARY KEY,
                    secret     VARCHAR(512) NOT NULL,
                    enabled_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
                )
            """
            await self._db.execute(create_sql, [])
            await self._db.execute(
                f"ALTER TABLE {_TABLE} ALTER COLUMN secret TYPE VARCHAR(512)",
                [],
            )
        else:
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {_TABLE} (
                    user_id    TEXT         PRIMARY KEY,
                    secret     VARCHAR(512) NOT NULL,
                    enabled_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """
            await self._db.execute(create_sql, [])
        self._initialized = True

    # ------------------------------------------------------------------
    # AdminMfaStoreProtocol
    # ------------------------------------------------------------------

    async def is_enabled(self, user_id: str) -> bool:
        """Return True when the user has a stored TOTP secret."""
        return await self.get_secret(user_id) is not None

    async def get_secret(self, user_id: str) -> str | None:
        """Return the stored TOTP secret for a user (None when disabled).

        Decrypts the stored value when an ``encryption_service`` is
        configured.  Rows written before encryption (raw base32) fall
        back to their raw value — a one-time read path; they are
        re-encrypted on the next ``save_secret``.
        """
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
        value = str(row.get("secret", ""))
        if self._encryption_service is None:
            return value
        try:
            return self._encryption_service.decrypt(value)
        except DecryptionError:
            return value

    async def save_secret(self, user_id: str, secret: str) -> None:
        """Persist (or refresh) the TOTP secret for a user.

        The value is encrypted at rest (ciphertext in ``secret``) when
        an ``encryption_service`` is configured, otherwise stored raw.
        """
        stored = (
            self._encryption_service.encrypt(secret)
            if self._encryption_service is not None
            else secret
        )
        await self._db.execute(
            f"""
            INSERT INTO {_TABLE} (user_id, secret)
            VALUES (?, ?)
            ON CONFLICT (user_id) DO UPDATE SET
                secret = excluded.secret,
                updated_at = {now_expr(self._db)}
            """,
            [user_id, stored],
        )

    async def disable(self, user_id: str) -> None:
        """Remove the TOTP secret for a user (2FA off)."""
        await self._db.execute(
            f"DELETE FROM {_TABLE} WHERE user_id = ?",
            [user_id],
        )


__all__ = ["AdminMfaSqlStore"]
