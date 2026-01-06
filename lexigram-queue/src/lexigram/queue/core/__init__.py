"""Core module initialization."""

from __future__ import annotations

from lexigram.queue.core.dlq import DeadLetterEntry, DeadLetterQueue
from lexigram.queue.core.outbox import OutboxEntry, TransactionalOutbox
from lexigram.queue.core.pipeline import MessagePipeline, MiddlewareBase

__all__ = [
    "DeadLetterEntry",
    "DeadLetterQueue",
    "MessagePipeline",
    "MiddlewareBase",
    "OutboxEntry",
    "TransactionalOutbox",
]
