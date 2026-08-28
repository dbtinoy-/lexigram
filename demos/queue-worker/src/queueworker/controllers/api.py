"""HTTP controls for the focused Lexigram queue-worker demo."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.queue.protocols import QueueProtocol
from lexigram.contracts.queue.types import BusMessage
from lexigram.web import Controller, get, post
from queueworker.services.processor import MessageProcessor


class QueueApiController(Controller):
    """Publish task messages and inspect the real ``MessageConsumer``."""

    prefix = "/api/queue"

    def __init__(
        self,
        queue: QueueProtocol | None = None,
        processor: MessageProcessor | None = None,
        max_retries: int = 3,
    ) -> None:
        self._queue = queue
        self._processor = processor
        self._max_retries = max_retries

    @post("/publish")
    async def publish(self, body: dict[str, Any]) -> dict[str, Any]:
        """Publish a Lexigram ``BusMessage`` to the worker's topic."""
        topic = body.get("topic", self._processor.topic)
        topic_error = self._topic_error(topic)
        if topic_error:
            return {"error": topic_error}

        message = BusMessage(
            topic=topic,
            payload=body.get("payload", {}),
            max_retries=self._max_retries,
        )
        published = await self._queue.publish(topic, message)
        return {
            "message_id": published.id,
            "topic": published.topic,
            "delivery": published.delivery_guarantee.value,
            "max_retries": published.max_retries,
        }

    @get("/processed")
    async def processed(self) -> dict[str, Any]:
        """Get the consumer's processed-message audit trail."""
        results = self._processor.get_processed()
        return {"count": len(results), "results": results}

    @get("/health")
    async def health(self) -> dict[str, Any]:
        """Report QueueProtocol and MessageConsumer readiness."""
        return {
            "status": "ok" if self._processor.is_running() else "starting",
            "service": "queueworker",
            "topic": self._processor.topic,
            "consumer_running": self._processor.is_running(),
        }

    def _topic_error(self, topic: str) -> str | None:
        """Keep the example intentionally scoped to one worker topic."""
        if not topic:
            return "Topic is required"
        if topic != self._processor.topic:
            return f"This worker listens only to the '{self._processor.topic}' topic"
        return None


__all__ = ["QueueApiController"]
