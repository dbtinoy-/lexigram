"""Database-persisted inbox store implementation.

Uses :class:`~lexigram.contracts.data.sql.database.DatabaseProviderProtocol`
so the underlying engine (PostgreSQL, MySQL, SQLite …) is fully decoupled.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.contracts.data.sql.database import DatabaseProviderProtocol
from lexigram.contracts.exceptions import DatabaseError
from lexigram.contracts.notification.inbox import InboxMessage
from lexigram.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_TABLE = "notification_inbox_messages"


class DatabaseInboxStore:
    """SQL-backed :class:`InboxStoreProtocol` implementation.

    Reads and writes to a single flat table.  The table must exist before
    the store is used; the expected DDL is::

        CREATE TABLE notification_inbox_messages (
            id          TEXT        PRIMARY KEY,
            user_id     TEXT        NOT NULL,
            title       TEXT        NOT NULL,
            body        TEXT        NOT NULL,
            read        BOOLEAN     NOT NULL DEFAULT FALSE,
            created_at  TIMESTAMPTZ NOT NULL,
            metadata    JSONB       NOT NULL DEFAULT '{}'
        );
        CREATE INDEX ON notification_inbox_messages (user_id, created_at DESC);

    Args:
        db: Database provider injected via DI.
        table: Table name. Defaults to ``notification_inbox_messages``.
    """

    def __init__(
        self,
        db: DatabaseProviderProtocol,
        *,
        table: str = _DEFAULT_TABLE,
    ) -> None:
        self._db = db
        self._table = table

    # ------------------------------------------------------------------
    # InboxStoreProtocol implementation
    # ------------------------------------------------------------------

    async def save(self, message: InboxMessage) -> None:
        """Persist *message* in the database.

        Args:
            message: The inbox message to store.
        """
        await self._db.execute_insert(
            self._table,
            {
                "id": message.id,
                "user_id": message.user_id,
                "title": message.title,
                "body": message.body,
                "read": message.read,
                "created_at": message.created_at,
                "metadata": message.metadata,
            },
        )
        logger.debug("inbox.db.saved", message_id=message.id, user_id=message.user_id)

    async def get(self, message_id: str) -> InboxMessage | None:
        """Return the message with *message_id*, or ``None``.

        Args:
            message_id: ID to look up.
        """
        result = await self._db.execute_query(
            f"SELECT * FROM {self._table} WHERE id = $1",  # noqa: S608
            [message_id],
        )
        if not result.rows:
            return None
        return self._row_to_message(result.rows[0])

    async def list_for_user(
        self,
        user_id: str,
        *,
        unread_only: bool = False,
    ) -> list[InboxMessage]:
        """Return messages for *user_id* in reverse-chronological order.

        Args:
            user_id: Filter to this user.
            unread_only: When ``True`` only unread messages are returned.
        """
        if unread_only:
            result = await self._db.execute_query(
                f"SELECT * FROM {self._table}"  # noqa: S608
                " WHERE user_id = $1 AND read = FALSE"
                " ORDER BY created_at DESC",
                [user_id],
            )
        else:
            result = await self._db.execute_query(
                f"SELECT * FROM {self._table}"  # noqa: S608
                " WHERE user_id = $1"
                " ORDER BY created_at DESC",
                [user_id],
            )
        return [self._row_to_message(row) for row in result.rows]

    async def mark_read(self, message_id: str, user_id: str) -> None:
        """Mark *message_id* as read, guarded by *user_id* ownership.

        Args:
            message_id: ID of the message to mark.
            user_id: Expected owner.
        """
        await self._db.execute_update(
            self._table,
            {"read": True},
            "id = $1 AND user_id = $2",
            [message_id, user_id],
        )
        logger.debug("inbox.db.marked_read", message_id=message_id, user_id=user_id)

    async def mark_all_read(self, user_id: str) -> None:
        """Mark every unread message for *user_id* as read.

        Args:
            user_id: Target user.
        """
        await self._db.execute_update(
            self._table,
            {"read": True},
            "user_id = $1 AND read = FALSE",
            [user_id],
        )
        logger.debug("inbox.db.all_marked_read", user_id=user_id)

    async def delete(self, message_id: str, user_id: str) -> None:
        """Delete *message_id*, guarded by *user_id* ownership.

        Args:
            message_id: ID to remove.
            user_id: Expected owner.
        """
        await self._db.execute_delete(
            self._table,
            "id = $1 AND user_id = $2",
            [message_id, user_id],
        )
        logger.debug("inbox.db.deleted", message_id=message_id, user_id=user_id)

    async def count_unread(self, user_id: str) -> int:
        """Return unread message count for *user_id*.

        Args:
            user_id: Target user.
        """
        result = await self._db.execute_query(
            f"SELECT COUNT(*) AS cnt FROM {self._table}"  # noqa: S608
            " WHERE user_id = $1 AND read = FALSE",
            [user_id],
        )
        if not result.rows:
            return 0
        return int(result.rows[0].get("cnt", 0))

    async def clear_all(self, user_id: str) -> int:
        """Delete all messages for *user_id*.

        Args:
            user_id: Target user.

        Returns:
            Number of messages deleted.
        """
        count_result = await self._db.execute_query(
            f"SELECT COUNT(*) AS cnt FROM {self._table}"  # noqa: S608
            " WHERE user_id = $1",
            [user_id],
        )
        count = int(count_result.rows[0].get("cnt", 0)) if count_result.rows else 0
        await self._db.execute_delete(
            self._table,
            "user_id = $1",
            [user_id],
        )
        logger.debug("inbox.db.cleared_all", user_id=user_id, count=count)
        return count

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Run a lightweight read-only database probe for inbox storage."""
        try:
            await self._db.execute_query(
                f"SELECT 1 FROM {self._table} LIMIT 1",  # noqa: S608
                [],
            )
        except (
            DatabaseError,
            ConnectionError,
            RuntimeError,
            TimeoutError,
            ValueError,
        ) as exc:
            return HealthCheckResult(
                component="inbox_store",
                status=HealthStatus.UNHEALTHY,
                error=str(exc),
                details={"backend": "database", "table": self._table},
            )

        return HealthCheckResult(
            component="inbox_store",
            status=HealthStatus.HEALTHY,
            details={"backend": "database", "table": self._table},
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_message(row: dict[str, Any]) -> InboxMessage:
        """Convert a raw DB row dict to an :class:`InboxMessage`.

        Args:
            row: Raw row returned by the database driver.

        Returns:
            Hydrated :class:`InboxMessage` instance.
        """
        created_at = row["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif not isinstance(created_at, datetime):
            created_at = datetime.now(UTC)

        metadata = row.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}

        return InboxMessage(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            title=str(row["title"]),
            body=str(row["body"]),
            read=bool(row.get("read", False)),
            created_at=created_at,
            metadata=metadata,
        )


__all__ = ["DatabaseInboxStore"]
