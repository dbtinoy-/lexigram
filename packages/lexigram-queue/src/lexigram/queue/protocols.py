"""Re-export queue protocol stubs."""

from __future__ import annotations

from lexigram.contracts.queue.protocols import (
    MessageConsumerProtocol,
    QueueProtocol,
)

__all__ = ["MessageConsumerProtocol", "QueueProtocol"]
