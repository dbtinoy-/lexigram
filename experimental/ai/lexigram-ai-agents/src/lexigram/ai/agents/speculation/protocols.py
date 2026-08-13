"""Package-internal protocols for speculative execution."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lexigram.contracts import (
    ToolProtocol,
)
from lexigram.contracts.ai.llm import ChatMessage


@runtime_checkable
class ToolCallPredictorProtocol(Protocol):
    """Predicts which tools the LLM is likely to call for a given query.

    Package-internal protocol. Not in contracts because it is only consumed
    by SpeculativeToolPreFetcher within lexigram-ai-agents.
    """

    def predict(
        self,
        query: str,
        available_tools: list[ToolProtocol],
        recent_history: list[ChatMessage] | None = None,
    ) -> list[ToolProtocol]:
        """Return tools ranked by likelihood of being called.

        Args:
            query: The current user query.
            available_tools: All tools registered in the agent.
            recent_history: Recent conversation turns for context.

        Returns:
            Tools sorted by predicted likelihood, most likely first.
        """
        ...
