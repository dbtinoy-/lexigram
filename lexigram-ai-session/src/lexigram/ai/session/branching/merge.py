"""Merge strategies for combining branched sessions."""

from __future__ import annotations

import copy
from dataclasses import replace
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lexigram.contracts.ai.session import SessionState


@runtime_checkable
class MergeStrategy(Protocol):
    """Protocol for merging a branch session back into a parent session.

    Implementors decide which turns and variables from the branch are
    incorporated into the parent when a branch is merged.
    """

    async def merge(self, parent: SessionState, branch: SessionState) -> SessionState:
        """Merge *branch* into *parent* and return the combined state.

        Args:
            parent: The original session state.
            branch: The forked branch to merge back.

        Returns:
            A new ``SessionState`` combining both sessions.
        """
        ...


class AppendMerge:
    """Append the branch's new turns (after the fork point) to the parent.

    Variables from the branch are shallow-merged into the parent, with
    branch values taking precedence for conflicting keys.
    """

    async def merge(self, parent: SessionState, branch: SessionState) -> SessionState:
        """Append new branch turns after the parent's last turn.

        Args:
            parent: The parent session state.
            branch: The branch session state.

        Returns:
            Merged ``SessionState`` with branch turns appended.
        """
        merged = copy.deepcopy(parent)

        # Identify turns that occurred after the fork (by timestamp comparison)
        fork_timestamp = parent.turns[-1].timestamp if parent.turns else None
        if fork_timestamp is not None:
            new_turns = [t for t in branch.turns if t.timestamp > fork_timestamp]
        else:
            new_turns = list(branch.turns)

        merged.turns.extend(new_turns)
        merged.variables.update(branch.variables)
        return replace(merged, turn_count=len(merged.turns))


class SelectiveMerge:
    """Cherry-pick specific turns from the branch by turn ID.

    Args:
        turn_ids: IDs of the branch turns to include in the merge.
    """

    def __init__(self, turn_ids: list[str]) -> None:
        self._turn_ids: set[str] = set(turn_ids)

    async def merge(self, parent: SessionState, branch: SessionState) -> SessionState:
        """Copy only the specified branch turns into the parent.

        Args:
            parent: The parent session state.
            branch: The branch session state.

        Returns:
            Merged ``SessionState`` with selected branch turns appended.
        """
        merged = copy.deepcopy(parent)
        selected = [t for t in branch.turns if t.turn_id in self._turn_ids]
        merged.turns.extend(selected)
        return replace(merged, turn_count=len(merged.turns))


__all__ = [
    "AppendMerge",
    "MergeStrategy",
    "SelectiveMerge",
]
