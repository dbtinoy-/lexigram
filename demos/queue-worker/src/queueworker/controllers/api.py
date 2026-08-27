"""Queue API — HTTP surface for message queue operations.

Controllers are thin: they validate input, call a service, and
return a response dict.  No business logic lives here.
"""

from __future__ import annotations

from typing import Any

from lexigram.web import Controller, get, post


class QueueApiController(Controller):
    """HTTP surface for message queue operations.

    Delegates to services for business logic.  Returns dicts that
    the framework serialises to JSON.
    """

    prefix = "/api/queue"

    def __init__(self, queue: object = None, processor: object = None) -> None:
        self._queue = queue
        self._processor = processor

    @post("/publish")
    async def publish(self, body: dict[str, Any]) -> dict[str, Any]:
        """Publish a message to the queue.

        Body: ``{"topic": "orders", "payload": {"order_id": "123"}}``
        """
        topic = body.get("topic", "")
        if not topic:
            return {"error": "Topic is required"}

        payload = body.get("payload", {})
        msg = await self._queue.publish(topic, payload)
        return {"message_id": msg.id, "topic": msg.topic}

    @post("/process")
    async def process(self, body: dict[str, Any]) -> dict[str, Any]:
        """Process a single message from the queue.

        Body: ``{"topic": "orders"}``
        """
        topic = body.get("topic", "")
        if not topic:
            return {"error": "Topic is required"}

        result = await self._processor.process_message(topic)
        if result is None:
            return {"message": "No messages to process"}
        return result

    @post("/process/batch")
    async def process_batch(self, body: dict[str, Any]) -> dict[str, Any]:
        """Process a batch of messages from the queue.

        Body: ``{"topic": "orders", "batch_size": 5}``
        """
        topic = body.get("topic", "")
        if not topic:
            return {"error": "Topic is required"}

        batch_size = body.get("batch_size", 10)
        results = await self._processor.process_batch(topic, batch_size=batch_size)
        return {"processed": len(results), "results": results}

    @get("/size")
    async def size(self, topic: str = "tasks") -> dict[str, Any]:
        """Get the number of messages in the queue."""
        size = await self._queue.size(topic)
        return {"topic": topic, "size": size}

    @get("/processed")
    async def processed(self) -> dict[str, Any]:
        """Get all processed messages."""
        results = self._processor.get_processed()
        return {"count": len(results), "results": results}

    @get("/health")
    async def health(self) -> dict[str, Any]:
        """Health check endpoint."""
        return {"status": "ok", "service": "queueworker"}


__all__ = ["QueueApiController"]
