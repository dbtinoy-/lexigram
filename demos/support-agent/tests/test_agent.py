"""Unit-level tests for the agent service (no boot here)."""

from __future__ import annotations

import asyncio

import pytest

from lexigram.contracts.ai.agents import AgentResponse
from lexigram.result import Ok

from support_agent.services.support_service import SupportAgent, build_support_agent
from support_agent.repository.scenarios import SCENARIOS


def _response() -> AgentResponse:
    return AgentResponse(
        message="done",
        steps=[],
        tool_calls=[],
        total_tokens=36,
        prompt_tokens=12,
        completion_tokens=24,
        total_cost=0.0,
        duration_ms=1.0,
        session_id=None,
        metadata={"strategy": "react"},
    )


class _RecordingExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[object, str]] = []

    async def run(self, *, agent: object, message: str, **kw: object):
        self.calls.append((agent, message))
        return Ok(_response())


class TestBuildSupportAgent:
    def test_builds_named_agent_with_tools_and_strategy(self) -> None:
        agent = build_support_agent()

        assert agent.name == "support-agent"
        assert len(agent.tools) == 3
        assert getattr(agent, "strategy", None) is not None


class TestScenariosRegistry:
    def test_three_scenarios_registered(self) -> None:
        assert set(SCENARIOS) == {"happy", "multi_tool", "failure"}
        assert all(len(s.script) >= 2 for s in SCENARIOS.values())
        assert {s.label for s in SCENARIOS.values()} == {
            "Happy path",
            "Multi-tool",
            "Failure",
        }


class TestSupportAgentFacade:
    def test_records_last_response(self) -> None:
        executor = _RecordingExecutor()
        facade = SupportAgent(executor=executor, agent=build_support_agent())

        result = asyncio.run(facade.ask("hi"))

        assert isinstance(result, Ok)
        assert facade.last_response is not None
        assert executor.calls[0][1] == "hi"

    def test_infra_error_raises_not_wrapped(self) -> None:
        class _Broken:
            async def run(self, **kw: object):
                raise RuntimeError("not booted")

        facade = SupportAgent(executor=_Broken(), agent=build_support_agent())
        with pytest.raises(RuntimeError, match="not booted"):
            asyncio.run(facade.ask("hi"))
