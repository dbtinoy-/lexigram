"""Multi-agent subpackage — group sessions with coordinated turn-taking."""

from __future__ import annotations

from lexigram.ai.session.multi_agent.group_session import GroupSession
from lexigram.ai.session.multi_agent.role_isolation import RoleIsolation
from lexigram.ai.session.multi_agent.turn_manager import (
    PriorityTurnManager,
    RoundRobinTurnManager,
    TopicBasedTurnManager,
    TurnManager,
)

__all__ = [
    "GroupSession",
    "PriorityTurnManager",
    "RoleIsolation",
    "RoundRobinTurnManager",
    "TopicBasedTurnManager",
    "TurnManager",
]
