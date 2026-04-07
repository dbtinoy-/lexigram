"""SQL-backed implementation of AdminLoginAttemptStoreProtocol.

Owns all DDL and DML for the ``admin_login_attempts`` table.  The service
layer depends only on ``AdminLoginAttemptStoreProtocol`` from
``lexigram.admin.auth.protocols`` — never on this class directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import uuid

from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.auth.types import AdminLoginAttempt

logger = get_logger(__name__)

_TABLE = "admin_login_attempts"


@inject
class AdminLoginAttemptSqlStore:
    """SQL-backed store for admin login attempt records.

    Implements ``AdminLoginAttemptStoreProtocol`` via structural subtyping.
    Manages the ``admin_login_attempts`` table including DDL bootstrap,
    failure counting for rate limiting, and attempt persistence.
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
        ``CREATE INDEX IF NOT EXISTS`` so concurrent callers are safe.

        Raises:
            Exception: Propagates any unexpected DDL failure so the caller
                surfaces the problem rather than silently skipping persistence.
        """
        if self._initialized:
            return

        try:
            await self._db.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_login_attempts (
                    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                    email         VARCHAR(255) NOT NULL,
                    ip_address    VARCHAR(45)  NOT NULL,
                    user_agent    TEXT         NOT NULL DEFAULT '',
                    success       BOOLEAN      NOT NULL DEFAULT FALSE,
                    failure_reason VARCHAR(50),
                    attempted_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
                )
                """,
                [],
            )
            await self._db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_admin_login_attempts_email_attempted_at
                    ON admin_login_attempts(email, attempted_at DESC)
                """,
                [],
            )
            await self._db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_admin_login_attempts_ip_attempted_at
                    ON admin_login_attempts(ip_address, attempted_at DESC)
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

    async def insert(self, attempt: AdminLoginAttempt) -> None:
        """Insert a login attempt record.

        Generates a fresh UUID when ``attempt.id`` is empty so callers may
        pass an uninitialised id without failing the NOT NULL constraint.

        Args:
            attempt: Login attempt data to persist.
        """
        await self.ensure_schema()
        attempt_id = attempt.id or str(uuid.uuid4())
        sql = (
            "INSERT INTO admin_login_attempts "
            "(id, email, ip_address, user_agent, success, failure_reason, attempted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)"
        )
        await self._db.execute(
            sql,
            (
                attempt_id,
                attempt.email,
                attempt.ip_address,
                attempt.user_agent,
                attempt.success,
                attempt.failure_reason,
                attempt.attempted_at,
            ),
        )
        logger.debug(
            "login_attempt.inserted",
            email=attempt.email,
            success=attempt.success,
            failure_reason=attempt.failure_reason,
        )

    async def count_recent_failures(self, email: str, since_seconds: int) -> int:
        """Count failed login attempts for email within the last N seconds.

        Args:
            email: Email address to query.
            since_seconds: Look-back window in seconds.

        Returns:
            Number of failed attempts within the window.
        """
        await self.ensure_schema()
        sql = (
            "SELECT COUNT(*) AS count FROM admin_login_attempts "
            "WHERE email = ? AND success = FALSE "
            f"AND attempted_at > NOW() - INTERVAL '{since_seconds} seconds'"
        )
        result = await self._db.execute_query(sql, [email])
        count = self._extract_count(result)
        logger.debug(
            "login_attempt.count_recent_failures",
            email=email,
            since_seconds=since_seconds,
            count=count,
        )
        return count

    async def count_recent_failures_by_ip(
        self, ip_address: str, since_seconds: int
    ) -> int:
        """Count failed login attempts from IP within the last N seconds.

        Args:
            ip_address: Client IP address to query.
            since_seconds: Look-back window in seconds.

        Returns:
            Number of failed attempts within the window.
        """
        await self.ensure_schema()
        sql = (
            "SELECT COUNT(*) AS count FROM admin_login_attempts "
            "WHERE ip_address = ? AND success = FALSE "
            f"AND attempted_at > NOW() - INTERVAL '{since_seconds} seconds'"
        )
        result = await self._db.execute_query(sql, [ip_address])
        count = self._extract_count(result)
        logger.debug(
            "login_attempt.count_recent_failures_by_ip",
            ip_address=ip_address,
            since_seconds=since_seconds,
            count=count,
        )
        return count

    async def clear_failures(self, email: str) -> None:
        """Delete all failure records for email.

        Called immediately after a successful login so subsequent failure
        counts start from zero.

        Args:
            email: Email address whose failure records to remove.
        """
        await self.ensure_schema()
        sql = "DELETE FROM admin_login_attempts WHERE email = ? AND success = FALSE"
        await self._db.execute(sql, (email,))
        logger.debug("login_attempt.failures_cleared", email=email)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_count(result: Any) -> int:
        """Normalise heterogeneous query result shapes into an integer count.

        Args:
            result: Raw result returned by ``execute_query``.

        Returns:
            The integer value of the ``count`` column, or ``0`` when absent.
        """
        if hasattr(result, "rows") and result.rows:
            return int(result.rows[0].get("count", 0))
        if isinstance(result, list) and result:
            row = result[0]
            if isinstance(row, dict):
                return int(row.get("count", 0))
        return 0


__all__ = ["AdminLoginAttemptSqlStore"]
