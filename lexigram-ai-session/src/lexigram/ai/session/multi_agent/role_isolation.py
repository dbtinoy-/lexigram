"""Per-agent memory scope isolation for multi-agent group sessions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.ai.session import SessionTurn


class RoleIsolation:
    """Control which turns each agent can see within a group session.

    By default all turns are visible to everyone. Role isolation allows
    marking individual turns as private to a specific agent, so sensitive
    reasoning by one agent is not leaked to peers.

    Turn visibility rules (checked in order):
    1. A turn tagged ``visible_to`` in its metadata is only shown to
       the listed agent names.
    2. A turn tagged ``hidden_from`` in its metadata is hidden from those
       agent names.
    3. Otherwise the turn is visible to everyone.
    """

    def filter_for_agent(
        self, turns: list[SessionTurn], agent_name: str
    ) -> list[SessionTurn]:
        """Return only the turns the given agent is allowed to see.

        Args:
            turns: Complete session turn list.
            agent_name: The agent whose view to compute.

        Returns:
            Filtered list of turns visible to *agent_name*.
        """
        visible: list[SessionTurn] = []
        for turn in turns:
            visible_to: list[str] | None = turn.metadata.get("visible_to")
            hidden_from: list[str] | None = turn.metadata.get("hidden_from")

            if visible_to is not None:
                if agent_name in visible_to:
                    visible.append(turn)
            elif hidden_from is not None:
                if agent_name not in hidden_from:
                    visible.append(turn)
            else:
                visible.append(turn)

        return visible


__all__ = ["RoleIsolation"]
