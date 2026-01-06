"""Transactional outbox pattern for reliable message publishing."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.queue.protocols import QueueProtocol
    from lexigram.contracts.queue.types import BusMessage

logger = get_logger(__name__)


@dataclass
class OutboxEntry:
    """Entry staged in the transactional outbox."""

    topic: str
    message: BusMessage
    published: bool = False


class TransactionalOutbox:
    """Stage messages within a transaction, flush atomically."""

    def __init__(self, queue: QueueProtocol) -> None:
        """Initialize outbox.

        Args:
            queue: Queue protocol to publish messages to.
        """
        self._queue = queue
        self._entries: list[OutboxEntry] = []

    def stage(self, topic: str, message: BusMessage) -> None:
        """Stage a message for publish within a transaction.

        Args:
            topic: Destination topic.
            message: Message to stage.
        """
        self._entries.append(OutboxEntry(topic=topic, message=message))

    async def flush(self) -> None:
        """Publish all staged messages that haven't been published yet."""
        pending = [e for e in self._entries if not e.published]
        if not pending:
            return

        results = await asyncio.gather(
            *[self._queue.publish(e.topic, e.message) for e in pending],
            return_exceptions=True,
        )

        for entry, result in zip(pending, results, strict=False):
            if isinstance(result, Exception):
                logger.error(
                    "outbox_flush_failed", topic=entry.topic, error=str(result)
                )
            else:
                entry.published = True

    def clear(self) -> None:
        """Clear all staged entries."""
        self._entries.clear()


__all__ = ["OutboxEntry", "TransactionalOutbox"]
