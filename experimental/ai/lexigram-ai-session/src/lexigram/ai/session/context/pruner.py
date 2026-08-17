"""Relevance-based conversation history pruner."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.ai.llm import ChatMessageProtocol


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase word tokens.

    Args:
        text: Input string.

    Returns:
        List of lowercase, whitespace-delimited tokens.
    """
    return [w.lower() for w in text.split() if w]


class RelevanceContextPruner:
    """Keyword-overlap relevance pruner for conversation history.

    Implements ``ContextPrunerProtocol``.  When the history exceeds
    ``max_turns``, system messages are always preserved and non-system
    turns are scored by keyword overlap with the current query plus a
    recency bonus, then the top-scoring turns are retained in their
    original chronological order.
    """

    async def prune(
        self,
        history: list[ChatMessageProtocol],
        current_query: str,
        max_turns: int,
    ) -> list[ChatMessageProtocol]:
        """Prune history to at most ``max_turns``, keeping relevant turns.

        Scoring formula per non-system turn::

            score = overlap_count + recency_ratio * 0.3

        where ``overlap_count`` is the number of tokens shared between the
        turn content and ``current_query``, and ``recency_ratio`` is the
        turn's normalised position in the non-system history (0 = oldest,
        1 = newest).

        Args:
            history: Full conversation history.
            current_query: The current user query for relevance scoring.
            max_turns: Maximum number of turns to retain.

        Returns:
            Pruned history in chronological order.
        """
        if len(history) <= max_turns:
            return list(history)

        system_msgs = [m for m in history if str(m.role).lower() == "system"]
        non_system = [m for m in history if str(m.role).lower() != "system"]

        system_count = len(system_msgs)
        available_slots = max_turns - system_count

        if available_slots <= 0:
            return system_msgs[:max_turns]

        query_tokens = set(_tokenize(current_query))
        total = len(non_system)
        normalization = max(total - 1, 1)

        scored: list[tuple[float, int, ChatMessageProtocol]] = []
        for i, msg in enumerate(non_system):
            content = str(msg.content) if msg.content is not None else ""
            msg_tokens = set(_tokenize(content))
            overlap = len(query_tokens & msg_tokens)
            recency = i / normalization
            score = float(overlap) + recency * 0.3
            scored.append((score, i, msg))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected_ids = {id(item[2]) for item in scored[:available_slots]}

        return [
            msg
            for msg in history
            if str(msg.role).lower() == "system" or id(msg) in selected_ids
        ]


__all__ = ["RelevanceContextPruner"]
