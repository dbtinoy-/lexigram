"""Inbox service — high-level user-facing inbox operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.notification.inbox import INBOX_SENT_HOOK, InboxMessage
from lexigram.hooks.ambient import fire as fire_hook
from lexigram.logging import get_logger
from lexigram.notification.inbox.memory import InMemoryInboxStore

if TYPE_CHECKING:
    from lexigram.contracts.notification.inbox import InboxStoreProtocol

logger = get_logger(__name__)


class InboxService:
    """High-level service for managing per-user inbox notifications.

    Wraps an :class:`InboxStoreProtocol` backend and exposes a clean API
    consumed by controllers, event handlers, or a notification bell widget.

    Defaults to :class:`InMemoryInboxStore` when no *store* is supplied so
    that the service can be used without DI wiring in simple scenarios (e.g.
    tests, CLI tools).  Production deployments should inject a
    :class:`DatabaseInboxStore` via the DI container.

    Args:
        store: Persistence backend.  Defaults to ``InMemoryInboxStore()``.
    """

    def __init__(
        self,
        store: InboxStoreProtocol | None = None,
    ) -> None:
        self._store: InboxStoreProtocol = store or InMemoryInboxStore()

    async def send(
        self,
        user_id: str,
        title: str,
        body: str,
        **metadata: Any,
    ) -> InboxMessage:
        """Create and persist an inbox notification for *user_id*.

        Keyword arguments beyond *body* are collected into the message
        ``metadata`` dict so callers can attach arbitrary context::

            await inbox.send(
                user_id="u1",
                title="Order shipped",
                body="Your order #123 is on the way.",
                order_id="123",
                tracking_url="https://example.com/track/123",
            )

        Args:
            user_id: Recipient user ID.
            title: Short notification title shown in list views.
            body: Full message body.
            **metadata: Arbitrary key-value pairs stored in ``metadata``.

        Returns:
            The newly created and persisted :class:`InboxMessage`.
        """
        message = InboxMessage.create(
            user_id=user_id,
            title=title,
            body=body,
            metadata=dict(metadata) if metadata else None,
        )
        await self._store.save(message)
        logger.info(
            "inbox.sent",
            message_id=message.id,
            user_id=user_id,
            title=title,
        )
        await fire_hook(
            INBOX_SENT_HOOK,
            message=message,
            user_id=user_id,
            title=title,
            body=body,
        )
        return message

    async def get_inbox(
        self,
        user_id: str,
        *,
        unread_only: bool = False,
    ) -> list[InboxMessage]:
        """Return inbox messages for *user_id*.

        Args:
            user_id: User whose inbox to fetch.
            unread_only: When ``True`` only unread messages are returned.

        Returns:
            Messages in reverse-chronological order.
        """
        return await self._store.list_for_user(user_id, unread_only=unread_only)

    async def get_message(self, message_id: str) -> InboxMessage | None:
        """Return a single inbox message by ID.

        Args:
            message_id: Message to retrieve.

        Returns:
            The message, or ``None`` if not found.
        """
        return await self._store.get(message_id)

    async def mark_read(self, message_id: str, user_id: str) -> None:
        """Mark *message_id* as read.

        The *user_id* guard ensures a user can only mark their own messages.

        Args:
            message_id: ID of the message to mark.
            user_id: Owning user (authorisation guard).
        """
        await self._store.mark_read(message_id, user_id)

    async def mark_all_read(self, user_id: str) -> None:
        """Mark all of *user_id*'s messages as read.

        Args:
            user_id: Target user.
        """
        await self._store.mark_all_read(user_id)

    async def delete(self, message_id: str, user_id: str) -> None:
        """Delete a message owned by *user_id*.

        Args:
            message_id: ID of the message to remove.
            user_id: Owning user (authorisation guard).
        """
        await self._store.delete(message_id, user_id)

    async def count_unread(self, user_id: str) -> int:
        """Return the unread message count for *user_id*.

        Args:
            user_id: Target user.

        Returns:
            Number of unread messages.
        """
        return await self._store.count_unread(user_id)

    async def clear_all(self, user_id: str) -> int:
        """Delete all messages for *user_id*.

        Args:
            user_id: Target user.

        Returns:
            Number of messages deleted.
        """
        count = await self._store.clear_all(user_id)
        logger.info("inbox.cleared_all", user_id=user_id, count=count)
        return count


__all__ = ["InboxService"]
