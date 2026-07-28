"""Tests for RunnableBranch."""
from __future__ import annotations

import pytest

from lexigram.ai.llm.runnable.lambda_ import RunnableLambda


class TestRunnableBranch:
    """Tests for RunnableBranch."""

    def test_branch_routes_to_first_match(self) -> None:
        """Branch should route to first matching predicate."""
        from lexigram.ai.llm.runnable.branch import RunnableBranch

        branch = RunnableBranch(
            branches=[
                (lambda x: x > 10, RunnableLambda(lambda x: f"big:{x}")),
                (lambda x: x > 5, RunnableLambda(lambda x: f"medium:{x}")),
            ],
            default=RunnableLambda(lambda x: f"small:{x}"),
        )

        assert branch.invoke(15) == "big:15"
        assert branch.invoke(7) == "medium:7"
        assert branch.invoke(3) == "small:3"

    @pytest.mark.asyncio
    async def test_branch_ainvoke(self) -> None:
        """Branch should work with ainvoke."""
        from lexigram.ai.llm.runnable.branch import RunnableBranch

        branch = RunnableBranch(
            branches=[
                (lambda x: x > 10, RunnableLambda(lambda x: f"big:{x}")),
            ],
            default=RunnableLambda(lambda x: f"small:{x}"),
        )

        assert await branch.ainvoke(15) == "big:15"
        assert await branch.ainvoke(3) == "small:3"

    def test_branch_no_match_uses_default(self) -> None:
        """Branch should use default when no predicate matches."""
        from lexigram.ai.llm.runnable.branch import RunnableBranch

        branch = RunnableBranch(
            branches=[
                (lambda x: x > 100, RunnableLambda(lambda x: "big")),
            ],
            default=RunnableLambda(lambda x: "default"),
        )

        assert branch.invoke(5) == "default"
