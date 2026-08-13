"""Group session — multiple agents sharing one session with coordinated turns."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from lexigram.ai.session.multi_agent.role_isolation import RoleIsolation
from lexigram.ai.session.multi_agent.turn_manager import (
    RoundRobinTurnManager,
    TurnManager,
)
from lexigram.contracts.ai.session import SessionState, SessionTurn
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class GroupSession:
    """A session shared by multiple agents with coordinated turn-taking.

    Wraps a ``SessionManagerImpl`` and a ``TurnManager`` to run a structured
    multi-agent conversation.  Each agent is called in the order determined
    by the turn manager, and each agent sees only the turns filtered by
    ``RoleIsolation``.

    Args:
        session_manager: Session lifecycle manager.
        turn_manager: Strategy for selecting the next speaking agent.
        role_isolation: Optional turn-visibility filter; defaults to all-visible.
    """

    def __init__(
        self,
        session_manager: Any,
        turn_manager: TurnManager | None = None,
        role_isolation: RoleIsolation | None = None,
    ) -> None:
        self._manager = session_manager
        self._turns: TurnManager = turn_manager or RoundRobinTurnManager()
        self._isolation = role_isolation or RoleIsolation()
        self._agents: dict[str, Any] = {}

    def add_agent(self, agent: Any, role: str = "participant") -> None:
        """Register an agent with the group session.

        Args:
            agent: An object with a ``name`` attribute and an async
                ``execute(message, history)`` method returning a ``Result``.
            role: Role label for turn management.
        """
        name = agent.name if hasattr(agent, "name") else str(agent)
        self._agents[name] = agent
        self._turns.register(name, role)

    async def run(
        self,
        session_id: str,
        initial_message: str,
        *,
        max_rounds: int = 10,
    ) -> SessionState:
        """Run the multi-agent conversation and return the final session state.

        Posts *initial_message* as a user turn then iterates until all agents
        are done or *max_rounds* cycles complete.

        Args:
            session_id: The session to run within (must already exist).
            initial_message: The opening user message.
            max_rounds: Maximum conversation rounds (passed to turn manager).

        Returns:
            Final ``SessionState`` after the conversation completes.
        """
        await self._manager.add_turn(
            session_id,
            SessionTurn(
                turn_id=str(uuid4()),
                role="user",
                content=initial_message,
                timestamp=datetime.now(UTC),
            ),
        )

        for round_num in range(max_rounds):
            next_agent_name = await self._turns.select_next(session_id)
            if next_agent_name is None:
                break

            agent = self._agents.get(next_agent_name)
            if agent is None:
                logger.warning(
                    "group_session_unknown_agent",
                    agent_name=next_agent_name,
                    session_id=session_id,
                )
                break

            state = await self._manager.get_state(session_id)
            if state is None:
                break

            visible_turns = self._isolation.filter_for_agent(
                state.turns, next_agent_name
            )

            try:
                result = await agent.execute(
                    message=visible_turns[-1].content if visible_turns else "",
                    history=[
                        {
                            "role": t.role,
                            "content": t.content,
                            "turn_id": t.turn_id,
                        }
                        for t in visible_turns
                    ],
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "group_session_agent_error",
                    agent_name=next_agent_name,
                    round=round_num,
                    error=str(exc),
                )
                break

            if result.is_ok():
                response = result.unwrap()
                message = (
                    response.message if hasattr(response, "message") else str(response)
                )
                await self._manager.add_turn(
                    session_id,
                    SessionTurn(
                        turn_id=str(uuid4()),
                        role="assistant",
                        content=message,
                        timestamp=datetime.now(UTC),
                        metadata={"agent": next_agent_name, "round": round_num},
                    ),
                )

            if await self._turns.is_complete(session_id):
                break

        return await self._manager.get_state(session_id)

    @property
    def agent_names(self) -> list[str]:
        """Names of all registered agents in registration order.

        Returns:
            List of agent names.
        """
        return list(self._agents)


__all__ = ["GroupSession"]
