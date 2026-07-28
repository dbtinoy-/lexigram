"""Unit tests for SessionAnalytics and compute function."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from lexigram.ai.session.analytics.core import compute
from lexigram.contracts.ai.session import SessionTurn


class TestSessionAnalytics:
    """Tests for SessionAnalytics dataclass."""

    async def test_single_turn_session(self, make_state, make_turn) -> None:
        """Analytics with one turn."""
        turn = make_turn(role="user", content="hello", tokens_used=10, cost=0.001)
        state = make_state(turns=[turn], total_tokens=10, total_cost=0.001)

        analytics = compute(state)

        assert analytics.session_id == state.session_id
        assert analytics.total_turns == 1
        assert analytics.total_tokens == 10
        assert analytics.total_cost == 0.001
        assert analytics.duration_seconds == 0.0
        assert analytics.avg_response_time_ms == 0.0

    async def test_no_turns_session(self, make_state) -> None:
        """Analytics with zero turns."""
        state = make_state()

        analytics = compute(state)

        assert analytics.session_id == state.session_id
        assert analytics.total_turns == 0
        assert analytics.total_tokens == 0
        assert analytics.total_cost == 0.0
        assert analytics.duration_seconds == 0.0
        assert analytics.avg_response_time_ms == 0.0
        assert analytics.tools_invoked == []

    async def test_multiple_turns_with_tools(self, make_state) -> None:
        """Analytics with tool calls."""
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        turn1 = SessionTurn(
            turn_id=str(uuid4()),
            role="user",
            content="hello",
            timestamp=base_time,
            tokens_used=10,
            cost=0.001,
            tool_calls=[{"name": "search"}],
        )

        turn2 = SessionTurn(
            turn_id=str(uuid4()),
            role="assistant",
            content="result",
            timestamp=base_time.replace(minute=1),
            tokens_used=20,
            cost=0.002,
            tool_calls=[{"name": "search"}, {"name": "calculate"}],
        )

        state = make_state(turns=[turn1, turn2], total_tokens=30, total_cost=0.003)

        analytics = compute(state)

        assert analytics.total_turns == 2
        assert analytics.total_tokens == 30
        assert analytics.total_cost == 0.003
        assert set(analytics.tools_invoked) == {"calculate", "search"}

    async def test_duration_calculation(self, make_state) -> None:
        """Elapsed time computation."""
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        turn1 = SessionTurn(
            turn_id=str(uuid4()),
            role="user",
            content="hello",
            timestamp=base_time,
            tokens_used=10,
            cost=0.001,
        )

        turn2 = SessionTurn(
            turn_id=str(uuid4()),
            role="assistant",
            content="hi",
            timestamp=base_time.replace(second=30),
            tokens_used=5,
            cost=0.0005,
        )

        state = make_state(turns=[turn1, turn2], total_tokens=15, total_cost=0.0015)

        analytics = compute(state)

        assert analytics.duration_seconds == 30.0

    async def test_average_response_time(self, make_state) -> None:
        """Avg response time calculation."""
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        turn1 = SessionTurn(
            turn_id=str(uuid4()),
            role="user",
            content="q1",
            timestamp=base_time,
            tokens_used=5,
            cost=0.001,
        )

        turn2 = SessionTurn(
            turn_id=str(uuid4()),
            role="assistant",
            content="a1",
            timestamp=base_time.replace(second=10),
            tokens_used=10,
            cost=0.002,
        )

        turn3 = SessionTurn(
            turn_id=str(uuid4()),
            role="user",
            content="q2",
            timestamp=base_time.replace(second=15),
            tokens_used=5,
            cost=0.001,
        )

        state = make_state(turns=[turn1, turn2, turn3], total_tokens=20, total_cost=0.004)

        analytics = compute(state)

        assert analytics.avg_response_time_ms == 7500.0


class TestComputeFunction:
    """Tests for the compute() function."""

    async def test_empty_turns(self, make_state) -> None:
        """compute() returns zeros for empty session."""
        state = make_state()
        analytics = compute(state)

        assert analytics.total_turns == 0
        assert analytics.total_tokens == 0
        assert analytics.total_cost == 0.0
        assert analytics.agents_used == []
        assert analytics.models_used == []
        assert analytics.tools_invoked == []

    async def test_agents_deduplication(self, make_state) -> None:
        """Providers are deduplicated."""
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        turns = []
        total_tokens = 0

        for i in range(3):
            turn = SessionTurn(
                turn_id=str(uuid4()),
                role="user",
                content=f"turn{i}",
                timestamp=base_time,
                tokens_used=10,
                provider="openai" if i % 2 == 0 else "anthropic",
            )
            turns.append(turn)
            total_tokens += 10

        state = make_state(turns=turns, total_tokens=total_tokens)
        analytics = compute(state)

        assert set(analytics.agents_used) == {"anthropic", "openai"}

    async def test_models_deduplication(self, make_state) -> None:
        """Model IDs are deduplicated."""
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        turns = []
        total_tokens = 0

        for i in range(3):
            turn = SessionTurn(
                turn_id=str(uuid4()),
                role="user",
                content=f"turn{i}",
                timestamp=base_time,
                tokens_used=10,
                model="gpt-4" if i % 2 == 0 else "claude-3",
            )
            turns.append(turn)
            total_tokens += 10

        state = make_state(turns=turns, total_tokens=total_tokens)
        analytics = compute(state)

        assert set(analytics.models_used) == {"claude-3", "gpt-4"}

    async def test_tool_names_extraction(self, make_state) -> None:
        """Tool names extracted from tool_calls format."""
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        turn1 = SessionTurn(
            turn_id=str(uuid4()),
            role="user",
            content="search",
            timestamp=base_time,
            tokens_used=5,
            tool_calls=[{"name": "web_search"}],
        )

        turn2 = SessionTurn(
            turn_id=str(uuid4()),
            role="assistant",
            content="found",
            timestamp=base_time,
            tokens_used=10,
            tool_calls=[{"function": {"name": "db_query"}}],
        )

        state = make_state(turns=[turn1, turn2], total_tokens=15)

        analytics = compute(state)

        assert analytics.tools_invoked == ["db_query", "web_search"]

    async def test_unsorted_turns_by_timestamp(self, make_state) -> None:
        """Duration computed correctly even if turns are unsorted."""
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        turn1 = SessionTurn(
            turn_id=str(uuid4()),
            role="assistant",
            content="late",
            timestamp=base_time.replace(second=10),
            tokens_used=5,
        )

        turn2 = SessionTurn(
            turn_id=str(uuid4()),
            role="user",
            content="early",
            timestamp=base_time,
            tokens_used=5,
        )

        state = make_state(turns=[turn1, turn2], total_tokens=10)

        analytics = compute(state)

        assert analytics.duration_seconds == 10.0
