"""In-memory inbox store implementation.

Suitable for unit tests and single-process deployments that do not
require durable notification persistence.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.contracts.notification.inbox import InboxMessage
from lexigram.logging import get_logger

logger = get_logger(__name__)


class InMemoryInboxStore:
    """In-process :class:`InboxStoreProtocol` implementation backed by a dict.

    Thread-safety note: this store is *not* thread-safe.  Within a single
    async event loop it is safe; for multi-threaded scenarios inject a
    SQL-backed :class:`DatabaseInboxStore` instead.
    """

    def __init__(self) -> None:
        self._store: dict[str, InboxMessage] = {}

    async def save(self, message: InboxMessage) -> None:
        """Persist *message* in memory.

        Args:
            message: The inbox message to store.
        """
        self._store[message.id] = message
        logger.debug("inbox.saved", message_id=message.id, user_id=message.user_id)

    async def get(self, message_id: str) -> InboxMessage | None:
        """Return the message with *message_id*, or ``None``.

        Args:
            message_id: ID to look up.
        """
        return self._store.get(message_id)

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
        results = [
            m
            for m in self._store.values()
            if m.user_id == user_id and (not unread_only or not m.read)
        ]
        results.sort(key=lambda m: m.created_at, reverse=True)
        return results

    async def mark_read(self, message_id: str, user_id: str) -> None:
        """Mark *message_id* as read if it belongs to *user_id*.

        ``InboxMessage`` is frozen; we create a replacement with
        ``read=True`` and update the store in-place.

        Args:
            message_id: ID of the message to mark.
            user_id: Expected owner.
        """
        msg = self._store.get(message_id)
        if msg is not None and msg.user_id == user_id and not msg.read:
            self._store[message_id] = replace(msg, read=True)
            logger.debug("inbox.marked_read", message_id=message_id, user_id=user_id)

    async def mark_all_read(self, user_id: str) -> None:
        """Mark every unread message for *user_id* as read.

        Args:
            user_id: Target user.
        """
        now = datetime.now(UTC)
        for mid, msg in list(self._store.items()):
            if msg.user_id == user_id and not msg.read:
                self._store[mid] = replace(msg, read=True)
        logger.debug("inbox.all_marked_read", user_id=user_id, ts=now.isoformat())

    async def delete(self, message_id: str, user_id: str) -> None:
        """Delete *message_id* if it belongs to *user_id*.

        Args:
            message_id: ID to remove.
            user_id: Expected owner.
        """
        msg = self._store.get(message_id)
        if msg is not None and msg.user_id == user_id:
            del self._store[message_id]
            logger.debug("inbox.deleted", message_id=message_id, user_id=user_id)

    async def count_unread(self, user_id: str) -> int:
        """Return unread message count for *user_id*.

        Args:
            user_id: Target user.
        """
        return sum(
            1 for m in self._store.values() if m.user_id == user_id and not m.read
        )

    async def clear_all(self, user_id: str) -> int:
        """Delete all messages for *user_id*.

        Args:
            user_id: Target user.

        Returns:
            Number of messages deleted.
        """
        ids = [mid for mid, m in self._store.items() if m.user_id == user_id]
        for mid in ids:
            del self._store[mid]
        logger.debug("inbox.cleared_all", user_id=user_id, count=len(ids))
        return len(ids)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Return health for the in-memory inbox backend."""
        _ = timeout
        return HealthCheckResult(
            component="inbox_store",
            status=HealthStatus.HEALTHY,
            details={"backend": "memory", "message_count": len(self._store)},
        )


__all__ = ["InMemoryInboxStore"]
