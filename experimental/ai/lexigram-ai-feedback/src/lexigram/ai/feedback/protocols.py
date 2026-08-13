"""Protocol re-exports for feedback — convenience surface for consumers."""

from __future__ import annotations

from lexigram.contracts.ai.feedback import FeedbackProtocol as FeedbackProtocol
from lexigram.contracts.ai.feedback import (
    FeedbackStoreProtocol as FeedbackStoreProtocol,
)

__all__ = [
    "FeedbackProtocol",
    "FeedbackStoreProtocol",
]
