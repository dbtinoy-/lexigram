"""Base class for message consumer workers."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.queue.protocols import QueueProtocol
    from lexigram.contracts.queue.types import BusMessage

logger = get_logger(__name__)


class MessageConsumer(abc.ABC):
    """Base class for message consumer workers.

    Subclass this and implement handle() to create a worker that
    subscribes to a topic and processes incoming messages.
    """

    topic: str

    def __init__(self, queue: QueueProtocol) -> None:
        """Initialize consumer.

        Args:
            queue: Queue protocol instance for subscribing.
        """
        self._queue = queue
        self._running: bool = False

    async def start(self) -> None:
        """Start consuming messages from the subscribed topic."""
        self._running = True
        await self._queue.subscribe(self.topic, self._dispatch)
        logger.info("consumer_started", topic=self.topic, consumer=type(self).__name__)

    async def stop(self) -> None:
        """Stop consuming messages."""
        self._running = False
        logger.info("consumer_stopped", topic=self.topic)

    async def _dispatch(self, message: BusMessage) -> None:
        """Dispatch a received message to the handler.

        Args:
            message: Message to dispatch.
        """
        if not self._running:
            return
        try:
            await self.handle(message)
        except Exception as exc:  # noqa: BLE001 — handler isolation
            logger.error("consumer_handler_error", topic=self.topic, error=str(exc))

    @abc.abstractmethod
    async def handle(self, message: BusMessage) -> None:
        """Handle a received message. Subclasses must implement this.

        Args:
            message: Message to handle.
        """
        ...


__all__ = ["MessageConsumer"]
