"""Integration tests for Phase 5 — cross-package protocol wiring.

Verifies that AgentExecutorImpl, RAGPipeline, LLMRouter, and MCPProvider
correctly accept and use the new optional protocols (working memory,
session manager, skill registry/executor, provider registry).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.agents.executor import AgentExecutorImpl
from lexigram.ai.agents.strategies import ReActStrategy
from lexigram.contracts.ai.agents import AgentResponse
from lexigram.contracts.ai.memory import MemoryEntry
from lexigram.contracts.ai.session import SessionState, SessionStatus
from lexigram.contracts.ai.skills import SkillDefinition, SkillResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MockAgent:
    """Minimal agent for testing."""

    def __init__(self) -> None:
        self.name = "test_agent"
        self.tools: list[Any] = []
        self.system_prompt = "You are a test agent."
        self.strategy = ReActStrategy()


def _make_response(message: str = "Hello") -> AgentResponse:
    return AgentResponse(
        message=message,
        total_tokens=10,
        duration_ms=50.0,
    )


# ---------------------------------------------------------------------------
# AgentExecutorImpl — new protocol integration
# ---------------------------------------------------------------------------


class TestExecutorWithWorkingMemory:
    """Verify AgentExecutorImpl uses WorkingMemoryProtocol."""

    def test_init_accepts_working_memory(self) -> None:
        wm = AsyncMock()
        executor = AgentExecutorImpl(working_memory=wm)
        assert executor._working_memory is wm

    def test_init_accepts_session_manager(self) -> None:
        sm = AsyncMock()
        executor = AgentExecutorImpl(session_manager=sm)
        assert executor._session_manager is sm

    def test_init_accepts_skill_registry(self) -> None:
        sr = MagicMock()
        executor = AgentExecutorImpl(skill_registry=sr)
        assert executor._skill_registry is sr

    def test_init_accepts_skill_executor(self) -> None:
        se = AsyncMock()
        executor = AgentExecutorImpl(skill_executor=se)
        assert executor._skill_executor is se

    def test_init_accepts_all_new_params(self) -> None:
        executor = AgentExecutorImpl(
            working_memory=AsyncMock(),
            session_manager=AsyncMock(),
            skill_executor=AsyncMock(),
            skill_registry=MagicMock(),
        )
        assert executor._working_memory is not None
        assert executor._session_manager is not None
        assert executor._skill_executor is not None
        assert executor._skill_registry is not None


class TestExecutorWorkingMemoryAssembly:
    """Verify working memory is used to assemble context."""

    @pytest.mark.asyncio
    async def test_working_memory_assemble_called_during_run(self) -> None:
        wm = AsyncMock()
        wm.assemble = AsyncMock(
            return_value=[
                MemoryEntry(
                    id="m1",
                    owner_id="owner-1",
                    content="prior context",
                    role="assistant",
                    timestamp=datetime.now(UTC),
                ),
            ]
        )
        wm.add = AsyncMock()

        agent = _MockAgent()
        # Mock strategy to return success
        strategy = AsyncMock()
        from lexigram.result import Ok

        strategy.execute = AsyncMock(return_value=Ok(_make_response()))
        agent.strategy = strategy

        executor = AgentExecutorImpl(working_memory=wm, llm=AsyncMock())
        result = await executor.run(agent=agent, message="Hello", session_id="s1")

        wm.assemble.assert_awaited_once()
        assert result.is_ok()


class TestExecutorSessionIntegration:
    """Verify session manager is used during execution."""

    @pytest.mark.asyncio
    async def test_session_resume_called(self) -> None:
        sm = AsyncMock()
        sm.resume = AsyncMock(
            return_value=SessionState(
                session_id="s1",
                user_id="u1",
                status=SessionStatus.ACTIVE,
            )
        )
        sm.add_turn = AsyncMock()

        agent = _MockAgent()
        strategy = AsyncMock()
        from lexigram.result import Ok

        strategy.execute = AsyncMock(return_value=Ok(_make_response()))
        agent.strategy = strategy

        executor = AgentExecutorImpl(session_manager=sm, llm=AsyncMock())
        result = await executor.run(
            agent=agent, message="Hello", session_id="s1", user_id="u1"
        )

        sm.resume.assert_awaited_once_with("s1")
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_session_turns_recorded(self) -> None:
        sm = AsyncMock()
        sm.resume = AsyncMock(
            return_value=SessionState(
                session_id="s1",
                user_id="u1",
                status=SessionStatus.ACTIVE,
            )
        )
        sm.add_turn = AsyncMock()

        agent = _MockAgent()
        strategy = AsyncMock()
        from lexigram.result import Ok

        strategy.execute = AsyncMock(return_value=Ok(_make_response("World")))
        agent.strategy = strategy

        executor = AgentExecutorImpl(session_manager=sm, llm=AsyncMock())
        await executor.run(agent=agent, message="Hello", session_id="s1", user_id="u1")

        # User turn + assistant turn
        assert sm.add_turn.await_count == 2


class TestExecutorSkillMerge:
    """Verify skill schemas are merged as tools."""

    @pytest.mark.asyncio
    async def test_skills_merged_into_tools(self) -> None:
        sr = MagicMock()
        sr.get_schemas = MagicMock(
            return_value=[
                {
                    "type": "function",
                    "function": {
                        "name": "search",
                        "description": "Search the web",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ]
        )

        agent = _MockAgent()
        strategy = AsyncMock()
        from lexigram.result import Ok

        strategy.execute = AsyncMock(return_value=Ok(_make_response()))
        agent.strategy = strategy

        executor = AgentExecutorImpl(skill_registry=sr, llm=AsyncMock())
        result = await executor.run(agent=agent, message="Hello")

        sr.get_schemas.assert_called_once()
        # The merged tools should include the skill schema
        call_kwargs = strategy.execute.call_args
        assert (
            len(call_kwargs.kwargs.get("tools", call_kwargs[1].get("tools", []))) >= 1
        )
        assert result.is_ok()


# ---------------------------------------------------------------------------
# RAGPipeline — memory enrichment
# ---------------------------------------------------------------------------


class TestRAGPipelineMemoryEnrichment:
    """Verify RAGPipeline uses working memory for context enrichment."""

    def test_pipeline_accepts_working_memory(self) -> None:
        from lexigram.ai.rag.config import PipelineConfig
        from lexigram.ai.rag.pipeline.builder import RAGPipeline

        wm = AsyncMock()
        pipeline = RAGPipeline(
            config=PipelineConfig(),
            stages=[],
            working_memory=wm,
        )
        assert pipeline._working_memory is wm


# ---------------------------------------------------------------------------
# MCP — skill adapter
# ---------------------------------------------------------------------------


class TestMCPSkillAdapter:
    """Verify SkillToolAdapter bridges skills to MCP tools."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_skill_definitions(self) -> None:
        from lexigram.ai.mcp.adapters.skill_adapter import SkillToolAdapter

        registry = MagicMock()
        registry.list_skills = MagicMock(
            return_value=[
                SkillDefinition(
                    name="calculator",
                    description="Basic math",
                    parameters_schema={"type": "object"},
                ),
            ]
        )

        adapter = SkillToolAdapter(skill_registry=registry)
        tools = await adapter.list_tools()

        assert len(tools) == 1
        assert tools[0]["name"] == "calculator"
        assert tools[0]["description"] == "Basic math"

    @pytest.mark.asyncio
    async def test_list_tools_empty_when_no_registry(self) -> None:
        from lexigram.ai.mcp.adapters.skill_adapter import SkillToolAdapter

        adapter = SkillToolAdapter()
        tools = await adapter.list_tools()
        assert tools == []

    @pytest.mark.asyncio
    async def test_call_tool_executes_skill(self) -> None:
        from lexigram.ai.mcp.adapters.skill_adapter import SkillToolAdapter
        from lexigram.result import Ok

        registry = MagicMock()
        registry.get = MagicMock(return_value=MagicMock())

        executor = AsyncMock()
        executor.execute = AsyncMock(
            return_value=Ok(
                SkillResult(
                    skill_name="calculator",
                    success=True,
                    output=42,
                )
            )
        )

        adapter = SkillToolAdapter(skill_registry=registry, skill_executor=executor)
        result = await adapter.call_tool("calculator", {"a": 1, "b": 2})

        assert result == 42
        executor.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_call_tool_raises_on_no_executor(self) -> None:
        from lexigram.ai.mcp.adapters.skill_adapter import SkillToolAdapter

        adapter = SkillToolAdapter()
        with pytest.raises(RuntimeError, match="No skill executor"):
            await adapter.call_tool("test", {})


# ---------------------------------------------------------------------------
# LLM Router — provider registry
# ---------------------------------------------------------------------------


class TestLLMRouterProviderRegistry:
    """Verify LLMRouter accepts optional provider registry."""

    def test_router_accepts_provider_registry(self) -> None:
        from lexigram.ai.llm.routing.config import LLMConfig
        from lexigram.ai.llm.routing.router import LLMRouter

        pr = MagicMock()
        pr.list_providers = MagicMock(return_value=["extra-provider"])

        router = LLMRouter(
            clients={},
            quota_backend=AsyncMock(),
            inference_logger=AsyncMock(),
            config=LLMConfig(),
            provider_registry=pr,
        )
        assert router._provider_registry is pr

    def test_router_works_without_provider_registry(self) -> None:
        from lexigram.ai.llm.routing.config import LLMConfig
        from lexigram.ai.llm.routing.router import LLMRouter

        router = LLMRouter(
            clients={},
            quota_backend=AsyncMock(),
            inference_logger=AsyncMock(),
            config=LLMConfig(),
        )
        assert router._provider_registry is None
