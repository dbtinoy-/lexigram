"""Unit tests for RelevanceContextPruner."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from lexigram.ai.session.context.pruner import RelevanceContextPruner


def _make_msg(role: str, content: str) -> MagicMock:
    """Create a mock ChatMessageProtocol object."""
    msg = MagicMock()
    msg.role = role
    msg.content = content
    return msg


class TestRelevanceContextPruner:
    """Tests for keyword-overlap relevance-based history pruning."""

    @pytest.mark.asyncio
    async def test_prune_returns_all_when_under_limit(self) -> None:
        """Returns all messages unchanged when history fits within max_turns."""
        pruner = RelevanceContextPruner()
        history = [_make_msg("user", "hello"), _make_msg("assistant", "world")]

        result = await pruner.prune(history, current_query="hello", max_turns=5)

        assert result == history

    @pytest.mark.asyncio
    async def test_prune_preserves_system_messages(self) -> None:
        """System messages are always retained regardless of score."""
        pruner = RelevanceContextPruner()
        sys_msg = _make_msg("system", "You are a helpful assistant")
        turns = [_make_msg("user", f"unrelated turn {i}") for i in range(5)]
        history = [sys_msg, *turns]

        # max_turns=3 → 1 system + 2 non-system
        result = await pruner.prune(history, current_query="cats", max_turns=3)

        assert sys_msg in result
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_prune_selects_relevant_turns(self) -> None:
        """High-overlap turns are preferred over irrelevant ones."""
        pruner = RelevanceContextPruner()
        relevant = _make_msg("user", "python asyncio coroutine await")
        irrelevant1 = _make_msg("user", "coffee cup morning")
        irrelevant2 = _make_msg("assistant", "sure thing buddy")
        history = [irrelevant1, irrelevant2, relevant]

        # max_turns=2, no system → keep 2 out of 3
        result = await pruner.prune(
            history, current_query="python asyncio", max_turns=2
        )

        assert relevant in result
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_prune_maintains_chronological_order(self) -> None:
        """Retained turns appear in their original chronological order."""
        pruner = RelevanceContextPruner()
        m1 = _make_msg("user", "python asyncio event loop")
        m2 = _make_msg("assistant", "random unrelated response xyz")
        m3 = _make_msg("user", "asyncio tasks coroutines python")
        m4 = _make_msg("assistant", "xyz foo bar baz qux")
        m5 = _make_msg("user", "unrelated banana orange fruit")
        history = [m1, m2, m3, m4, m5]

        result = await pruner.prune(
            history, current_query="python asyncio", max_turns=3
        )

        assert len(result) == 3
        # Verify chronological order is preserved among selected messages
        result_indices = [history.index(m) for m in result]
        assert result_indices == sorted(result_indices)
