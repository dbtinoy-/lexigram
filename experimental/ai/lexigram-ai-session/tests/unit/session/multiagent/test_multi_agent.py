"""Unit tests for multi-agent components."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from lexigram.contracts.ai.session import SessionTurn
from lexigram.ai.session.multi_agent.role_isolation import RoleIsolation
from lexigram.ai.session.multi_agent.turn_manager import (
    PriorityTurnManager,
    RoundRobinTurnManager,
    TopicBasedTurnManager,
)
from lexigram.ai.session.multi_agent.group_session import GroupSession


def _turn(content: str = "hello", metadata: dict | None = None) -> SessionTurn:
    return SessionTurn(
        turn_id=str(uuid4()),
        role="user",
        content=content,
        timestamp=datetime.now(UTC),
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# RoundRobinTurnManager
# ---------------------------------------------------------------------------


class TestRoundRobinTurnManager:
    async def test_returns_agents_in_order(self) -> None:
        mgr = RoundRobinTurnManager(max_rounds=2)
        mgr.register("alice", "participant")
        mgr.register("bob", "participant")
        picks = [await mgr.select_next("s") for _ in range(4)]
        assert picks == ["alice", "bob", "alice", "bob"]

    async def test_returns_none_after_max_rounds(self) -> None:
        mgr = RoundRobinTurnManager(max_rounds=1)
        mgr.register("alice", "participant")
        mgr.register("bob", "participant")
        await mgr.select_next("s")
        await mgr.select_next("s")
        assert await mgr.select_next("s") is None

    async def test_is_complete_false_initially(self) -> None:
        mgr = RoundRobinTurnManager(max_rounds=2)
        mgr.register("a", "p")
        assert not await mgr.is_complete("s")

    async def test_is_complete_true_after_rounds_exhausted(self) -> None:
        mgr = RoundRobinTurnManager(max_rounds=1)
        mgr.register("a", "p")
        await mgr.select_next("s")  # exhausts 1 round
        assert await mgr.is_complete("s")

    async def test_filter_visible_returns_all(self) -> None:
        mgr = RoundRobinTurnManager()
        turns = [_turn(), _turn()]
        assert mgr.filter_visible(turns, agent_name="x") == turns

    async def test_returns_none_with_no_agents(self) -> None:
        mgr = RoundRobinTurnManager()
        assert await mgr.select_next("s") is None


# ---------------------------------------------------------------------------
# PriorityTurnManager
# ---------------------------------------------------------------------------


class TestPriorityTurnManager:
    async def test_higher_priority_picked_first(self) -> None:
        mgr = PriorityTurnManager(priorities={"low": 1, "high": 10}, max_rounds=5)
        mgr.register("high", "p")
        mgr.register("low", "p")
        first = await mgr.select_next("s")
        assert first == "high"

    async def test_all_agents_selected_per_round(self) -> None:
        mgr = PriorityTurnManager(priorities={"a": 1, "b": 2}, max_rounds=1)
        mgr.register("a", "p")
        mgr.register("b", "p")
        picks = [await mgr.select_next("s"), await mgr.select_next("s")]
        assert set(picks) == {"a", "b"}

    async def test_returns_none_when_rounds_exhausted(self) -> None:
        mgr = PriorityTurnManager(priorities={"x": 1}, max_rounds=1)
        mgr.register("x", "p")
        await mgr.select_next("s")
        assert await mgr.select_next("s") is None

    async def test_is_complete_after_max_rounds(self) -> None:
        mgr = PriorityTurnManager(priorities={"x": 1}, max_rounds=1)
        mgr.register("x", "p")
        await mgr.select_next("s")
        assert await mgr.is_complete("s")


# ---------------------------------------------------------------------------
# TopicBasedTurnManager
# ---------------------------------------------------------------------------


class TestTopicBasedTurnManager:
    async def test_routes_by_keyword_match(self) -> None:
        mgr = TopicBasedTurnManager(topic_map={"weather": "weather_agent"}, max_rounds=5)
        mgr.register("weather_agent", "specialist")
        session_id = "sess"
        mgr.record_turns(session_id, [_turn("what is the weather today?")])
        agent = await mgr.select_next(session_id)
        assert agent == "weather_agent"

    async def test_falls_back_to_default_agent(self) -> None:
        mgr = TopicBasedTurnManager(
            topic_map={"finance": "finance_agent"},
            fallback_agent="general_agent",
            max_rounds=5,
        )
        mgr.register("general_agent", "p")
        session_id = "sess"
        mgr.record_turns(session_id, [_turn("tell me a joke")])
        agent = await mgr.select_next(session_id)
        assert agent == "general_agent"

    async def test_returns_none_when_no_fallback_and_no_match(self) -> None:
        mgr = TopicBasedTurnManager(topic_map={"x": "xbot"}, max_rounds=5)
        mgr.record_turns("s", [_turn("no match here")])
        assert await mgr.select_next("s") is None

    async def test_returns_none_after_max_rounds(self) -> None:
        mgr = TopicBasedTurnManager(
            topic_map={}, fallback_agent="bot", max_rounds=1
        )
        mgr.register("bot", "p")
        mgr.record_turns("s", [_turn()])
        await mgr.select_next("s")
        assert await mgr.select_next("s") is None

    async def test_is_complete_after_max_delegations(self) -> None:
        mgr = TopicBasedTurnManager(topic_map={}, fallback_agent="bot", max_rounds=1)
        mgr.register("bot", "p")
        mgr.record_turns("s", [_turn()])
        await mgr.select_next("s")
        assert await mgr.is_complete("s")


# ---------------------------------------------------------------------------
# RoleIsolation
# ---------------------------------------------------------------------------


class TestRoleIsolation:
    def test_all_turns_visible_by_default(self) -> None:
        iso = RoleIsolation()
        turns = [_turn(), _turn()]
        assert iso.filter_for_agent(turns, "alice") == turns

    def test_visible_to_restricts_to_named_agents(self) -> None:
        iso = RoleIsolation()
        secret = _turn("alice only", metadata={"visible_to": ["alice"]})
        public = _turn("public")
        result = iso.filter_for_agent([secret, public], "bob")
        assert secret not in result
        assert public in result

    def test_hidden_from_excludes_specific_agents(self) -> None:
        iso = RoleIsolation()
        hidden = _turn("not for alice", metadata={"hidden_from": ["alice"]})
        result_alice = iso.filter_for_agent([hidden], "alice")
        result_bob = iso.filter_for_agent([hidden], "bob")
        assert result_alice == []
        assert result_bob == [hidden]

    def test_visible_to_takes_precedence_over_hidden_from(self) -> None:
        """visible_to is checked first — hidden_from is only applied if visible_to absent."""
        iso = RoleIsolation()
        # visible_to set — only alice sees it
        turn = _turn("conflicting", metadata={"visible_to": ["alice"], "hidden_from": ["alice"]})
        assert iso.filter_for_agent([turn], "alice") == [turn]
        assert iso.filter_for_agent([turn], "bob") == []


# ---------------------------------------------------------------------------
# GroupSession
# ---------------------------------------------------------------------------


def _make_agent(name: str, response: str = "ok") -> Any:
    """Build a mock agent with name, execute returning an ok Result."""
    agent = MagicMock()
    agent.name = name
    ok_result = MagicMock()
    ok_result.is_ok.return_value = True
    ok_result.unwrap.return_value = MagicMock(message=response)
    agent.execute = AsyncMock(return_value=ok_result)
    return agent


class TestGroupSession:
    async def test_run_posts_initial_user_turn(self, manager) -> None:
        gs = GroupSession(session_manager=manager)
        agent = _make_agent("bot")
        gs.add_agent(agent)
        state = await manager.create(user_id="u1")
        final = await gs.run(state.session_id, "hello world", max_rounds=1)
        contents = [t.content for t in final.turns]
        assert "hello world" in contents

    async def test_run_agent_adds_response_turn(self, manager) -> None:
        gs = GroupSession(session_manager=manager, turn_manager=RoundRobinTurnManager(max_rounds=1))
        agent = _make_agent("bot", response="I am bot")
        gs.add_agent(agent)
        state = await manager.create(user_id="u1")
        final = await gs.run(state.session_id, "go", max_rounds=1)
        contents = [t.content for t in final.turns]
        assert "I am bot" in contents

    async def test_run_calls_agent_with_visible_history(self, manager) -> None:
        gs = GroupSession(session_manager=manager, turn_manager=RoundRobinTurnManager(max_rounds=1))
        agent = _make_agent("bot")
        gs.add_agent(agent)
        state = await manager.create(user_id="u1")
        await gs.run(state.session_id, "question", max_rounds=1)
        agent.execute.assert_called_once()
        _, kwargs = agent.execute.call_args
        assert "history" in kwargs

    async def test_agent_names_property(self) -> None:
        gs = GroupSession(session_manager=MagicMock())
        gs.add_agent(_make_agent("alice"))
        gs.add_agent(_make_agent("bob"))
        assert gs.agent_names == ["alice", "bob"]

    async def test_run_stops_when_agent_errors(self, manager) -> None:
        """Group session must stop gracefully if an agent raises."""
        gs = GroupSession(session_manager=manager, turn_manager=RoundRobinTurnManager(max_rounds=3))

        err_agent = MagicMock()
        err_agent.name = "crasher"
        err_agent.execute = AsyncMock(side_effect=RuntimeError("oops"))
        gs.add_agent(err_agent)

        state = await manager.create(user_id="u1")
        final = await gs.run(state.session_id, "start", max_rounds=3)
        assert final is not None  # should return state even on error
