"""SQL-backed implementation of AdminAccountLockoutStoreProtocol.

Owns all DDL and DML for the ``admin_account_lockouts`` table.  The service
layer depends only on ``AdminAccountLockoutStoreProtocol`` from
``lexigram.admin.auth.protocols`` — never on this class directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import uuid

from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from datetime import datetime

    from lexigram.admin.auth.types import AdminLockoutInfo

from lexigram.admin.auth.types import AdminLockoutStatus

logger = get_logger(__name__)

_TABLE = "admin_account_lockouts"


@inject
class AdminAccountLockoutSqlStore:
    """SQL-backed store for admin account lockout records.

    Implements ``AdminAccountLockoutStoreProtocol`` via structural subtyping.
    Manages the ``admin_account_lockouts`` table including DDL bootstrap,
    active-lockout queries, lockout creation, and lockout clearing.
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
        """Create table and indexes if they do not exist.

        Safe to call multiple times — idempotent after the first successful
        run.  Uses ``CREATE TABLE IF NOT EXISTS`` and
        ``CREATE UNIQUE INDEX IF NOT EXISTS`` so concurrent callers are safe.

        Raises:
            Exception: Propagates any unexpected DDL failure so the caller
                surfaces the problem rather than silently skipping persistence.
        """
        if self._initialized:
            return

        try:
            await self._db.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_account_lockouts (
                    id                   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                    email                VARCHAR(255) NOT NULL,
                    locked_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                    unlock_at            TIMESTAMPTZ,
                    consecutive_failures INTEGER      NOT NULL DEFAULT 0,
                    is_permanent         BOOLEAN      NOT NULL DEFAULT FALSE,
                    is_active            BOOLEAN      NOT NULL DEFAULT TRUE,
                    unlocked_at          TIMESTAMPTZ,
                    deactivated_at       TIMESTAMPTZ
                )
                """,
                [],
            )
            await self._db.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_account_lockouts_email_active
                    ON admin_account_lockouts(email) WHERE is_active = TRUE
                """,
                [],
            )
            await self._db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_admin_account_lockouts_email
                    ON admin_account_lockouts(email, locked_at DESC)
                """,
                [],
            )
            self._initialized = True
            logger.info("✅ %s schema ready", _TABLE)
        except Exception as _schema_err:  # noqa: BLE001 — DDL may raise DB-specific errors; log and propagate
            logger.exception("Failed to initialise %s schema", _TABLE)
            raise

    # ------------------------------------------------------------------
    # DML
    # ------------------------------------------------------------------

    async def get_active_lockout(self, email: str) -> AdminLockoutInfo | None:
        """Get active lockout for email, or ``None`` if the account is not locked.

        Checks ``is_active = TRUE`` and whether the lockout is still in effect
        (permanent, or ``unlock_at`` is in the future).  Expired temporary
        lockouts are deactivated transparently before returning ``None``.

        Args:
            email: Email address to check.

        Returns:
            ``AdminLockoutInfo`` when an active lockout exists, ``None``
            otherwise.
        """
        await self.ensure_schema()
        sql = (
            "SELECT id, email, locked_at, unlock_at, consecutive_failures, is_permanent "
            "FROM admin_account_lockouts "
            "WHERE email = ? AND is_active = TRUE"
        )
        result = await self._db.execute_query(sql, [email])
        rows = self._extract_rows(result)
        if not rows:
            return None

        row = dict(rows[0])
        is_permanent: bool = bool(row.get("is_permanent", False))
        unlock_at: Any = row.get("unlock_at")

        # A non-permanent lockout is only active while unlock_at is in the future.
        if not is_permanent and unlock_at is not None:
            # Ask the DB whether the lockout has expired — avoids timezone issues.
            expired_sql = (
                "UPDATE admin_account_lockouts "
                "SET is_active = FALSE, deactivated_at = NOW() "
                "WHERE email = ? AND is_active = TRUE AND is_permanent = FALSE "
                "AND unlock_at <= NOW()"
            )
            await self._db.execute(expired_sql, [email])

            # Re-check: if the row is gone, the lockout has expired.
            recheck_result = await self._db.execute_query(sql, [email])
            recheck_rows = self._extract_rows(recheck_result)
            if not recheck_rows:
                logger.debug("lockout.expired_deactivated", email=email)
                return None
            row = dict(recheck_rows[0])
            is_permanent = bool(row.get("is_permanent", False))
            unlock_at = row.get("unlock_at")

        status = (
            AdminLockoutStatus.PERMANENT if is_permanent else AdminLockoutStatus.LOCKED
        )

        from lexigram.admin.auth.types import (
            AdminLockoutInfo,  # local import avoids circularity at module level
        )

        lockout = AdminLockoutInfo(
            status=status,
            consecutive_failures=int(row.get("consecutive_failures", 0)),
            locked_at=row.get("locked_at"),
            unlock_at=unlock_at,
            is_permanent=is_permanent,
        )
        logger.debug(
            "lockout.active_found",
            email=email,
            status=status,
            consecutive_failures=lockout.consecutive_failures,
        )
        return lockout

    async def create_lockout(
        self,
        email: str,
        consecutive_failures: int,
        unlock_at: datetime | None,
        is_permanent: bool,
    ) -> None:
        """Create or replace the active lockout for email.

        Deactivates any existing active lockout first so the unique partial
        index on ``(email) WHERE is_active = TRUE`` is never violated.

        Args:
            email: Email address to lock.
            consecutive_failures: Total consecutive failure count to record.
            unlock_at: UTC datetime when the lock expires (``None`` if
                ``is_permanent`` is ``True``).
            is_permanent: Whether the lock requires manual admin intervention
                to clear.
        """
        await self.ensure_schema()

        # 1. Deactivate any existing active lockout.
        deactivate_sql = (
            "UPDATE admin_account_lockouts "
            "SET is_active = FALSE, deactivated_at = NOW() "
            "WHERE email = ? AND is_active = TRUE"
        )
        await self._db.execute(deactivate_sql, (email,))

        # 2. Insert the new lockout record.
        lockout_id = str(uuid.uuid4())
        insert_sql = (
            "INSERT INTO admin_account_lockouts "
            "(id, email, consecutive_failures, unlock_at, is_permanent, is_active) "
            "VALUES (?, ?, ?, ?, ?, TRUE)"
        )
        await self._db.execute(
            insert_sql,
            (
                lockout_id,
                email,
                consecutive_failures,
                unlock_at,
                is_permanent,
            ),
        )
        logger.info(
            "lockout.created",
            email=email,
            consecutive_failures=consecutive_failures,
            is_permanent=is_permanent,
            unlock_at=str(unlock_at) if unlock_at is not None else None,
        )

    async def clear_lockout(self, email: str) -> None:
        """Deactivate any active lockout for email.

        Called on successful login or explicit admin unlock.  Safe to call
        when no active lockout exists — the UPDATE simply affects zero rows.

        Args:
            email: Email address to unlock.
        """
        await self.ensure_schema()
        sql = (
            "UPDATE admin_account_lockouts "
            "SET is_active = FALSE, unlocked_at = NOW() "
            "WHERE email = ? AND is_active = TRUE"
        )
        await self._db.execute(sql, (email,))
        logger.debug("lockout.cleared", email=email)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_rows(result: Any) -> list[Any]:
        """Normalise heterogeneous query result shapes into a plain list.

        Args:
            result: Raw result returned by ``execute_query``.

        Returns:
            A list of row-like objects (dicts or record proxies).
        """
        if hasattr(result, "rows"):
            return list(result.rows)
        if isinstance(result, list):
            return result
        return []


__all__ = ["AdminAccountLockoutSqlStore"]
