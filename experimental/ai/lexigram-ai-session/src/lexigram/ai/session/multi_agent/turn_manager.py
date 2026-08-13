"""Turn managers — decide which agent acts next in a group session."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.ai.session import SessionTurn

logger = get_logger(__name__)


@runtime_checkable
class TurnManager(Protocol):
    """Protocol for multi-agent turn selection.

    Implementations decide which agent should speak next and whether
    the conversation should continue.
    """

    def register(self, agent_name: str, role: str) -> None:
        """Register an agent with this turn manager.

        Args:
            agent_name: Unique name of the agent.
            role: Role of the agent (e.g. ``participant``, ``coordinator``).
        """
        ...

    async def select_next(self, session_id: str) -> str | None:
        """Return the name of the next agent to act, or None to stop.

        Args:
            session_id: The currently active group session.

        Returns:
            Agent name, or ``None`` when the conversation should end.
        """
        ...

    async def is_complete(self, session_id: str) -> bool:
        """Return True when the group conversation should terminate.

        Args:
            session_id: The group session ID.

        Returns:
            True if the conversation is complete.
        """
        ...

    def filter_visible(
        self, turns: list[SessionTurn], *, agent_name: str
    ) -> list[SessionTurn]:
        """Filter to only the turns visible to the given agent.

        Args:
            turns: Full turn list from the session.
            agent_name: The agent whose visibility to apply.

        Returns:
            Subset of turns the agent is allowed to see.
        """
        ...


class RoundRobinTurnManager:
    """Cycle through registered agents in registration order.

    Each call to :meth:`select_next` advances to the next agent in the list,
    wrapping around when the end is reached.  Returns ``None`` after a
    configurable number of total rounds.

    Args:
        max_rounds: Total rounds before the conversation is considered complete.
    """

    def __init__(self, max_rounds: int = 10) -> None:
        self._agents: list[str] = []
        self._roles: dict[str, str] = {}
        self._index: int = 0
        self._round_count: int = 0
        self._max_rounds = max_rounds

    def register(self, agent_name: str, role: str) -> None:
        """Register an agent for round-robin participation.

        Args:
            agent_name: Unique agent name.
            role: Agent role label.
        """
        if agent_name not in self._agents:
            self._agents.append(agent_name)
        self._roles[agent_name] = role

    async def select_next(self, session_id: str) -> str | None:
        """Return the next agent in the rotation, or ``None`` when done.

        Args:
            session_id: Unused; kept for protocol compatibility.

        Returns:
            Agent name or ``None``.
        """
        if not self._agents or self._round_count >= self._max_rounds:
            return None
        agent = self._agents[self._index % len(self._agents)]
        self._index += 1
        if self._index % len(self._agents) == 0:
            self._round_count += 1
        return agent

    async def is_complete(self, session_id: str) -> bool:
        """Return True after *max_rounds* full cycles.

        Args:
            session_id: Unused; kept for protocol compatibility.

        Returns:
            True when the conversation is complete.
        """
        return self._round_count >= self._max_rounds

    def filter_visible(
        self, turns: list[SessionTurn], *, agent_name: str
    ) -> list[SessionTurn]:
        """All turns are visible to all agents in round-robin mode.

        Args:
            turns: Full session turn list.
            agent_name: The agent querying visibility.

        Returns:
            All turns unchanged.
        """
        return turns


class PriorityTurnManager:
    """Select agents by explicit priority; highest-priority agent goes first.

    Agents with higher priority values speak first. After each full rotation
    at the highest priority, lower-priority agents get a chance.

    Args:
        priorities: Mapping of agent name → integer priority (higher = first).
        max_rounds: Maximum full cycles before completion.
    """

    def __init__(
        self, priorities: dict[str, int] | None = None, max_rounds: int = 10
    ) -> None:
        self._priorities: dict[str, int] = priorities or {}
        self._roles: dict[str, str] = {}
        self._turn_count: int = 0
        self._max_rounds = max_rounds

    def register(self, agent_name: str, role: str) -> None:
        """Register an agent.

        Args:
            agent_name: Agent name.
            role: Agent role label.
        """
        self._roles[agent_name] = role
        if agent_name not in self._priorities:
            self._priorities[agent_name] = 0

    async def select_next(self, session_id: str) -> str | None:
        """Return the highest-priority agent that has not yet spoken this round.

        Args:
            session_id: Unused; kept for protocol compatibility.

        Returns:
            Agent name or ``None``.
        """
        if not self._priorities:
            return None
        total_agents = len(self._priorities)
        if total_agents == 0:
            return None
        full_rounds = self._turn_count // total_agents
        if full_rounds >= self._max_rounds:
            return None
        agents_sorted = sorted(
            self._priorities, key=lambda a: self._priorities[a], reverse=True
        )
        pick_index = self._turn_count % total_agents
        self._turn_count += 1
        return agents_sorted[pick_index]

    async def is_complete(self, session_id: str) -> bool:
        """Return True after *max_rounds* full cycles.

        Args:
            session_id: Unused; kept for protocol compatibility.

        Returns:
            True when the conversation is complete.
        """
        total_agents = max(len(self._priorities), 1)
        return (self._turn_count // total_agents) >= self._max_rounds

    def filter_visible(
        self, turns: list[SessionTurn], *, agent_name: str
    ) -> list[SessionTurn]:
        """All turns visible to all agents in priority mode.

        Args:
            turns: Full session turn list.
            agent_name: The querying agent name.

        Returns:
            All turns unchanged.
        """
        return turns


class TopicBasedTurnManager:
    """Route to agents based on keyword/topic detection in the latest turn.

    Args:
        topic_map: Mapping of keyword (lowercase) → agent name.
        fallback_agent: Agent to use when no topic match is found.
        max_rounds: Maximum total delegations before completion.
    """

    def __init__(
        self,
        topic_map: dict[str, str],
        fallback_agent: str | None = None,
        max_rounds: int = 10,
    ) -> None:
        self._topic_map = {k.lower(): v for k, v in topic_map.items()}
        self._fallback = fallback_agent
        self._roles: dict[str, str] = {}
        self._delegations: int = 0
        self._max_rounds = max_rounds
        self._last_turns: dict[str, list[SessionTurn]] = {}

    def register(self, agent_name: str, role: str) -> None:
        """Register an agent.

        Args:
            agent_name: Agent name.
            role: Agent role label.
        """
        self._roles[agent_name] = role

    async def select_next(self, session_id: str) -> str | None:
        """Select an agent based on the content of the most recent turn.

        Falls back to the configured fallback agent if no keyword matches.

        Args:
            session_id: Session ID for retrieving the last known turns.

        Returns:
            Agent name or ``None``.
        """
        if self._delegations >= self._max_rounds:
            return None

        turns = self._last_turns.get(session_id, [])
        latest_content = turns[-1].content.lower() if turns else ""

        for keyword, agent in self._topic_map.items():
            if keyword in latest_content:
                self._delegations += 1
                return agent

        if self._fallback:
            self._delegations += 1
            return self._fallback
        return None

    def record_turns(self, session_id: str, turns: list[SessionTurn]) -> None:
        """Update the local turn cache used for topic detection.

        Args:
            session_id: Session ID.
            turns: Current turn list for that session.
        """
        self._last_turns[session_id] = turns

    async def is_complete(self, session_id: str) -> bool:
        """Return True after *max_rounds* delegations.

        Args:
            session_id: Unused; kept for protocol compatibility.

        Returns:
            True when the conversation is complete.
        """
        return self._delegations >= self._max_rounds

    def filter_visible(
        self, turns: list[SessionTurn], *, agent_name: str
    ) -> list[SessionTurn]:
        """All turns visible in topic-based mode.

        Args:
            turns: Full session turn list.
            agent_name: The querying agent name.

        Returns:
            All turns unchanged.
        """
        return turns


__all__ = [
    "PriorityTurnManager",
    "RoundRobinTurnManager",
    "TopicBasedTurnManager",
    "TurnManager",
]
