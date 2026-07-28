"""Session analytics — turn count, token usage, cost, and duration tracking.

``SessionAnalytics`` is a frozen dataclass computed from a :class:`SessionState`
snapshot.  Use :func:`compute` to derive a complete analytics report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from datetime import datetime

    from lexigram.contracts.ai.session import SessionState

logger = get_logger(__name__)


@dataclass(frozen=True)
class SessionAnalytics:
    """Computed analytics for a single session.

    All fields are derived from :class:`~lexigram.contracts.ai.session.SessionState`
    and its :class:`~lexigram.contracts.ai.session.SessionTurn` records.

    Attributes:
        session_id: The session this report covers.
        total_turns: Number of turns (all roles) in the session.
        total_tokens: Cumulative tokens across all turns.
        total_cost: Cumulative cost (USD) across all turns.
        duration_seconds: Wall-clock time from first to last turn.  0 if fewer
            than two turns exist.
        agents_used: Deduplicated list of provider names seen across turns.
        tools_invoked: Deduplicated flat list of tool names referenced in
            ``SessionTurn.tool_calls``.
        avg_response_time_ms: Average milliseconds between consecutive turns.
            0.0 if fewer than two turns.
        models_used: Deduplicated list of model identifiers used across turns.
    """

    session_id: str
    total_turns: int
    total_tokens: int
    total_cost: float
    duration_seconds: float
    agents_used: list[str] = field(default_factory=list)
    tools_invoked: list[str] = field(default_factory=list)
    avg_response_time_ms: float = 0.0
    models_used: list[str] = field(default_factory=list)


def compute(state: SessionState) -> SessionAnalytics:
    """Derive :class:`SessionAnalytics` from a :class:`SessionState`.

    Args:
        state: The session state snapshot to analyse.

    Returns:
        Immutable analytics report.

    Example::

        analytics = compute(session_state)
        logger.info(
            "session_complete",
            session_id=analytics.session_id,
            turns=analytics.total_turns,
            cost=analytics.total_cost,
        )
    """
    turns = state.turns

    # Duration
    duration_seconds = 0.0
    avg_response_ms = 0.0
    if len(turns) >= 2:
        sorted_turns = sorted(turns, key=lambda t: t.timestamp)
        first: datetime = sorted_turns[0].timestamp
        last: datetime = sorted_turns[-1].timestamp
        delta = last - first
        duration_seconds = delta.total_seconds()
        # Average gap between consecutive turns in ms
        gaps: list[float] = []
        for i in range(1, len(sorted_turns)):
            gap_ms = (
                sorted_turns[i].timestamp - sorted_turns[i - 1].timestamp
            ).total_seconds() * 1000
            gaps.append(gap_ms)
        avg_response_ms = sum(gaps) / len(gaps) if gaps else 0.0

    # Agents / providers
    agents: list[str] = sorted({t.provider for t in turns if t.provider})

    # Models
    models: list[str] = sorted({t.model for t in turns if t.model})

    # Tools invoked (flat list from all turn_calls)
    tool_names: set[str] = set()
    for turn in turns:
        for call in turn.tool_calls:
            name = call.get("name") or call.get("function", {}).get("name")
            if name:
                tool_names.add(name)
    tools_invoked = sorted(tool_names)

    return SessionAnalytics(
        session_id=state.session_id,
        total_turns=len(turns),
        total_tokens=state.total_tokens,
        total_cost=state.total_cost,
        duration_seconds=duration_seconds,
        agents_used=agents,
        tools_invoked=tools_invoked,
        avg_response_time_ms=avg_response_ms,
        models_used=models,
    )


__all__ = ["SessionAnalytics", "compute"]
