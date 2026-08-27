"""Message processor — processes messages from the queue."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class MessageProcessor:
    """Processes messages from the queue.

    Demonstrates how to consume and process messages from a queue.
    """

    def __init__(self, queue: Any) -> None:
        self._queue = queue
        self._processed: list[dict[str, Any]] = []

    async def process_message(self, topic: str) -> dict[str, Any] | None:
        """Process a single message from the queue."""
        msg = await self._queue.consume(topic)
        if msg is None:
            return None

        result = {
            "message_id": msg.id,
            "topic": msg.topic,
            "payload": msg.payload,
            "processed_at": datetime.now(UTC).isoformat(),
        }
        self._processed.append(result)
        return result

    async def process_batch(
        self, topic: str, batch_size: int = 10
    ) -> list[dict[str, Any]]:
        """Process a batch of messages from the queue."""
        results = []
        for _ in range(batch_size):
            result = await self.process_message(topic)
            if result is None:
                break
            results.append(result)
        return results

    def get_processed(self) -> list[dict[str, Any]]:
        """Get all processed messages."""
        return list(self._processed)

    def clear_processed(self) -> int:
        """Clear the processed messages log."""
        count = len(self._processed)
        self._processed.clear()
        return count
