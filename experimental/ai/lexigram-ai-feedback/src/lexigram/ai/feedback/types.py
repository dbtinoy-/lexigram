"""Type definitions for AI Feedback - re-exported from contracts.

This module re-exports FeedbackItem and FeedbackType from
lexigram.contracts.ai.feedback for convenience. Use those imports
directly for new code.
"""

from __future__ import annotations

# Re-export from contracts where these types are centralized
from lexigram.contracts.ai.feedback import FeedbackItem, FeedbackType

__all__ = [
    "FeedbackItem",
    "FeedbackType",
]
