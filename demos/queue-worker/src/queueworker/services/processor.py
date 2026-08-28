"""Queue consumer for the demo's one task topic."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lexigram.contracts.queue.types import BusMessage
from lexigram.queue.consumers.consumer import MessageConsumer


class MessageProcessor(MessageConsumer):
    """Lexigram ``MessageConsumer`` that records handled task messages."""

    def __init__(self, queue: Any, topic: str = "tasks") -> None:
        super().__init__(queue)
        self.topic = topic
        self._processed: list[dict[str, Any]] = []

    async def handle(self, message: BusMessage) -> None:
        """Handle one bus message and keep a browser-readable audit trail."""
        self._processed.append(
            {
                "message_id": message.id,
                "topic": message.topic,
                "payload": message.payload,
                "processed_at": datetime.now(UTC).isoformat(),
            }
        )

    @property
    def processed_count(self) -> int:
        """Return the number of messages handled by this consumer."""
        return len(self._processed)

    def is_running(self) -> bool:
        """Return whether the Lexigram consumer subscription is active."""
        return self._running

    def get_processed(self) -> list[dict[str, Any]]:
        """Return a snapshot of processed messages."""
        return list(self._processed)
