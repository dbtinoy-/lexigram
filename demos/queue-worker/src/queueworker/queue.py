"""In-memory queue — simple message queue for demo purposes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
import uuid


@dataclass
class QueueMessage:
    """A message in the queue."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    retries: int = 0


class InMemoryQueue:
    """Simple in-memory message queue for demo purposes."""

    def __init__(self) -> None:
        self._messages: list[QueueMessage] = []
        self._consumers: dict[str, Any] = {}

    async def publish(self, topic: str, payload: dict[str, Any]) -> QueueMessage:
        """Publish a message to the queue."""
        msg = QueueMessage(topic=topic, payload=payload)
        self._messages.append(msg)
        return msg

    async def consume(self, topic: str) -> QueueMessage | None:
        """Consume a message from the queue."""
        for i, msg in enumerate(self._messages):
            if msg.topic == topic:
                return self._messages.pop(i)
        return None

    async def peek(self, topic: str) -> list[QueueMessage]:
        """Peek at messages without consuming."""
        return [msg for msg in self._messages if msg.topic == topic]

    async def size(self, topic: str) -> int:
        """Get the number of messages for a topic."""
        return len([msg for msg in self._messages if msg.topic == topic])

    async def clear(self, topic: str) -> int:
        """Clear all messages for a topic."""
        original = len(self._messages)
        self._messages = [msg for msg in self._messages if msg.topic != topic]
        return original - len(self._messages)
