"""StateDiff — incremental diff/apply for session state snapshots."""

from __future__ import annotations

import copy
from dataclasses import replace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.ai.session import SessionState, SessionTurn


class StateDiff:
    """Compute and apply incremental differences between session states.

    Reduces checkpoint storage cost by storing only what changed between
    consecutive checkpoints rather than full state copies.
    """

    @staticmethod
    def compute(old: SessionState, new: SessionState) -> dict[str, Any]:
        """Return a dict containing only the fields that changed.

        Compares *old* and *new* and returns a minimal diff that, when
        applied to *old*, reproduces *new*.

        Args:
            old: The baseline session state.
            new: The updated session state.

        Returns:
            Mapping of changed field names to their new values.
        """
        diff: dict[str, Any] = {}

        if len(new.turns) > len(old.turns):
            diff["new_turns"] = new.turns[len(old.turns) :]

        if new.variables != old.variables:
            diff["variables"] = new.variables

        if new.active_tools != old.active_tools:
            diff["active_tools"] = new.active_tools

        if new.active_skills != old.active_skills:
            diff["active_skills"] = new.active_skills

        if new.status != old.status:
            diff["status"] = new.status

        if new.system_prompt != old.system_prompt:
            diff["system_prompt"] = new.system_prompt

        diff["metrics"] = {
            "total_tokens": new.total_tokens,
            "total_cost": new.total_cost,
            "turn_count": new.turn_count,
        }

        return diff

    @staticmethod
    def apply(base: SessionState, diff: dict[str, Any]) -> SessionState:
        """Apply a diff produced by :meth:`compute` to reproduce the new state.

        Args:
            base: The baseline session state.
            diff: A dict previously returned by :meth:`compute`.

        Returns:
            A new ``SessionState`` with the diff applied.
        """
        state = copy.deepcopy(base)

        new_turns: list[SessionTurn] = diff.get("new_turns", [])
        if new_turns:
            state.turns.extend(new_turns)

        # Build a dict of updates to apply all at once with replace()
        updates: dict[str, Any] = {}

        if "variables" in diff:
            updates["variables"] = diff["variables"]

        if "active_tools" in diff:
            updates["active_tools"] = diff["active_tools"]

        if "active_skills" in diff:
            updates["active_skills"] = diff["active_skills"]

        if "status" in diff:
            updates["status"] = diff["status"]

        if "system_prompt" in diff:
            updates["system_prompt"] = diff["system_prompt"]

        if "metrics" in diff:
            updates["total_tokens"] = diff["metrics"]["total_tokens"]
            updates["total_cost"] = diff["metrics"]["total_cost"]
            updates["turn_count"] = diff["metrics"]["turn_count"]

        if updates:
            state = replace(state, **updates)

        return state


__all__ = ["StateDiff"]
