"""In-process batch publisher for fan-out message publishing.

Stages messages in memory and publishes them in a single ``flush()`` call.
Entries are process-local and do not survive restarts. For crash-safe
delivery support the durable outbox instead: ``OutboxStoreProtocol`` in
``lexigram.contracts.data.outbox`` with the SQL implementation in
``lexigram.sql.outbox`` (``SQLOutboxStore`` + ``OutboxPublisher``).
"""

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
class PendingPublish:
    """Message staged for batched publishing."""

    topic: str
    message: BusMessage
    published: bool = False


class BatchedPublisher:
    """Batch in-memory publish calls for a single atomic flush within one process.

    Messages staged via :meth:`stage` are held in memory only. ``flush()``
    publishes every unpublished entry concurrently; entries whose publish
    fails stay unpublished and are retried on the next ``flush()``.

    Note:
        This class is purely in-memory — staged entries are lost on process
        restart or when the instance is discarded without a ``flush()``. It
        provides no crash-safety or cross-restart durability guarantee. For
        durable, crash-safe publishing use the store-based outbox
        (``OutboxStoreProtocol`` in ``lexigram.contracts.data.outbox`` with
        ``lexigram.sql.outbox.SQLOutboxStore`` and
        ``lexigram.sql.outbox.OutboxPublisher``) inside the caller's
        database transaction.

    Example:
        ```python
        publisher = BatchedPublisher(queue)
        publisher.stage("orders.created", BusMessage(topic="orders.created", payload=data))
        await publisher.flush()
        ```
    """

    def __init__(self, queue: QueueProtocol) -> None:
        """Initialize publisher.

        Args:
            queue: Queue protocol to publish messages to.
        """
        self._queue = queue
        self._entries: list[PendingPublish] = []

    def stage(self, topic: str, message: BusMessage) -> None:
        """Stage a message locally for the next flush.

        Args:
            topic: Destination topic.
            message: Message to stage.
        """
        self._entries.append(PendingPublish(topic=topic, message=message))

    async def flush(self) -> None:
        """Publish all staged messages that haven't been published yet.

        Failed publishes are logged and remain unpublished so the next
        ``flush()`` retries them. Publish failures never raise.
        """
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
                    "batch_publish_failed", topic=entry.topic, error=str(result)
                )
            else:
                entry.published = True

    def clear(self) -> None:
        """Clear all staged entries."""
        self._entries.clear()


__all__ = ["BatchedPublisher", "PendingPublish"]
