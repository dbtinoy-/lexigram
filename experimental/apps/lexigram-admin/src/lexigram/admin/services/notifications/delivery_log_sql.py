"""SQL-backed email delivery log (R46, docs/09-01-2026/42-email-delivery-log.md).

Owns all DDL and DML for the ``admin_email_log`` table — the persistent
outbox record behind the "Recent deliveries" section of the Email
delivery page. Attached to ``AdminNotificationService`` best-effort at
mount time; a broken log must never break a send, so every caller wraps
access in its own try/except.
"""

from __future__ import annotations

from typing import Any
import uuid

from lexigram.admin.sql_dialect import is_postgres
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.logging import get_logger

logger = get_logger(__name__)

_TABLE = "admin_email_log"
_SUBJECT_MAX = 255
_ERROR_MAX = 500


class AdminEmailLogSqlStore:
    """Persistent record of email hand-offs to the mailer backend.

    "Success" means the backend accepted the message, not that it
    reached an inbox — the UI says so explicitly.
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        """Initialise with a resolved database provider.

        Args:
            db: Framework database provider exposing ``execute`` and
                ``execute_query``.
        """
        self._db = db
        self._initialized = False

    async def ensure_schema(self) -> None:
        """Create the table and index if they do not exist (idempotent)."""
        if self._initialized:
            return
        if is_postgres(self._db):
            create_sql = """
                CREATE TABLE IF NOT EXISTS admin_email_log (
                    id                TEXT         PRIMARY KEY,
                    notification_type VARCHAR(64)  NOT NULL,
                    recipient         VARCHAR(255) NOT NULL,
                    subject           VARCHAR(255) NOT NULL,
                    success           BOOLEAN      NOT NULL,
                    error             TEXT,
                    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
                )
            """
        else:
            create_sql = """
                CREATE TABLE IF NOT EXISTS admin_email_log (
                    id                TEXT         PRIMARY KEY,
                    notification_type VARCHAR(64)  NOT NULL,
                    recipient         VARCHAR(255) NOT NULL,
                    subject           VARCHAR(255) NOT NULL,
                    success           BOOLEAN      NOT NULL,
                    error             TEXT,
                    created_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """
        await self._db.execute(create_sql, [])
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_admin_email_log_created "
            "ON admin_email_log(created_at DESC)",
            [],
        )
        self._initialized = True
        logger.debug("email_log.schema_ready")

    async def record(
        self,
        notification_type: str,
        recipient: str,
        subject: str,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Append one delivery attempt; prunes opportunistically.

        Args:
            notification_type: Template/type name (e.g. ``password_reset``).
            recipient: Destination email address.
            subject: Rendered subject line (truncated defensively).
            success: Whether the backend accepted the message.
            error: Failure detail when ``success`` is False.
        """
        await self.ensure_schema()
        await self._db.execute(
            f"INSERT INTO {_TABLE} "  # noqa: S608 — table name is a module constant, never user input
            "(id, notification_type, recipient, subject, success, error) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                str(uuid.uuid4()),
                str(notification_type)[:64],
                str(recipient)[:255],
                str(subject)[:_SUBJECT_MAX],
                bool(success),
                (str(error)[:_ERROR_MAX] if error else None),
            ],
        )
        await self.prune()

    async def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the newest delivery rows.

        Args:
            limit: Maximum number of rows.

        Returns:
            Raw row dicts ordered by ``created_at`` descending.
        """
        await self.ensure_schema()
        sql = (
            "SELECT notification_type, recipient, subject, success, error, "
            f"created_at FROM {_TABLE} "  # noqa: S608 — constant table name
            "ORDER BY created_at DESC, id DESC "
            f"LIMIT {int(limit)}"  # int() guards LIMIT injection (store pattern)
        )
        result = await self._db.execute_query(sql, [])
        return [dict(r) for r in self._extract_rows(result)]

    async def prune(self, keep: int = 1000) -> None:
        """Delete everything older than the newest ``keep`` rows.

        Called after each :meth:`record` so the table cannot grow without
        bound; cheap because the id subquery is bounded by the index.

        Args:
            keep: Number of newest rows to retain.
        """
        await self.ensure_schema()
        await self._db.execute(
            f"DELETE FROM {_TABLE} WHERE id NOT IN "  # noqa: S608 — constant table name
            f"(SELECT id FROM {_TABLE} ORDER BY created_at DESC, id DESC "
            f"LIMIT {int(keep)})",  # int() guards LIMIT injection
            [],
        )

    @staticmethod
    def _extract_rows(result: Any) -> list[Any]:
        """Normalise heterogeneous query result shapes into a plain list."""
        rows = getattr(result, "rows", None)
        if rows is not None:
            return list(rows)
        if isinstance(result, list):
            return result
        return []
