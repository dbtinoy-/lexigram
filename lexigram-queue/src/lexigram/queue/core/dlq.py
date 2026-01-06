"""Dead Letter Queue (DLQ) for handling failed messages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.queue.types import BusMessage

logger = get_logger(__name__)


@dataclass
class DeadLetterEntry:
    """Entry in the dead letter queue."""

    message: BusMessage
    error: str
    failed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    retry_count: int = 0


class DeadLetterQueue:
    """In-memory dead letter queue for storing failed messages."""

    def __init__(self, max_size: int = 1000) -> None:
        """Initialize DLQ.

        Args:
            max_size: Maximum number of entries to store.
        """
        self._entries: list[DeadLetterEntry] = []
        self._max_size = max_size

    async def push(self, message: BusMessage, error: str) -> None:
        """Add a failed message to the DLQ.

        Args:
            message: The message that failed.
            error: Error description.
        """
        entry = DeadLetterEntry(message=message, error=error)
        if len(self._entries) >= self._max_size:
            self._entries.pop(0)
        self._entries.append(entry)
        logger.warning("dlq_entry_added", topic=message.topic, error=error)

    async def drain(self) -> list[DeadLetterEntry]:
        """Remove and return all entries from the DLQ.

        Returns:
            List of dead letter entries.
        """
        entries, self._entries = self._entries, []
        return entries

    @property
    def size(self) -> int:
        """Return current number of entries in DLQ."""
        return len(self._entries)


__all__ = ["DeadLetterEntry", "DeadLetterQueue"]
