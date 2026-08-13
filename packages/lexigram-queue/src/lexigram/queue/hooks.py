"""Root hook payload surface for lexigram-queue.

Defines canonical payload dataclasses for message-queue lifecycle hook points.
Actual hook registration and invocation use the framework's string-keyed
``HookRegistryProtocol`` action/filter APIs.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "MessageConsumedHook",
    "MessagePublishedHook",
    "QueueDrainedHook",
]


@dataclass(frozen=True, kw_only=True)
class MessagePublishedHook:
    """Payload fired when a message is published to a queue or topic.

    Attributes:
        queue_name: Name of the queue or topic the message was published to.
        message_type: Type label of the published message.
    """

    queue_name: str
    message_type: str


@dataclass(frozen=True, kw_only=True)
class MessageConsumedHook:
    """Payload fired when a message is successfully consumed by a handler.

    Attributes:
        queue_name: Name of the queue or topic the message came from.
        message_type: Type label of the consumed message.
    """

    queue_name: str
    message_type: str


@dataclass(frozen=True, kw_only=True)
class QueueDrainedHook:
    """Payload fired when a queue is fully drained (all pending messages processed).

    Attributes:
        queue_name: Name of the queue that was drained.
    """

    queue_name: str
