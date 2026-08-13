"""Scenario tests for full AI orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_full_ai_orchestration_scenario() -> None:
    """A scenario test that touches LLM, RAG, and Agents together."""
    from lexigram.ai.di.provider import AIProvider
    from lexigram.contracts import HealthCheckResult, HealthStatus
    
    # Check dependencies
    try:
        from lexigram.ai.llm.config import ClientConfig as LLMConfig
        from lexigram.ai.rag.config import RAGConfig
        from lexigram.ai.agents.executor.executor import AgentExecutorImpl
    except ImportError:
        pytest.skip("Full AI stack not available for scenario test")

    provider = AIProvider()
    
    # Mock LLM
    mock_llm_sub = MagicMock()
    mock_llm_sub.health_check = AsyncMock(return_value=HealthCheckResult(component="llm", status=HealthStatus.HEALTHY))
    mock_llm_client = AsyncMock()
    mock_llm_client.complete = AsyncMock(return_value="LLM Response")
    mock_llm_sub._llm_client = mock_llm_client
    provider._llm_sub = mock_llm_sub
    
    # Mock RAG
    mock_rag_sub = MagicMock()
    mock_rag_sub.health_check = AsyncMock(return_value=HealthCheckResult(component="rag", status=HealthStatus.HEALTHY))
    mock_pipeline = AsyncMock()
    mock_pipeline.process = AsyncMock(side_effect=lambda ctx: ctx)
    mock_rag_sub._pipeline = mock_pipeline
    provider._rag_sub = mock_rag_sub
    
    # Mock Agents
    mock_agent_sub = MagicMock()
    mock_agent_sub.health_check = AsyncMock(return_value=HealthCheckResult(component="agents", status=HealthStatus.HEALTHY))
    mock_executor = AsyncMock()
    mock_executor.run = AsyncMock(return_value=MagicMock(is_ok=lambda: True, unwrap=lambda: MagicMock(message="Agent Response")))
    mock_agent_sub._executor = mock_executor
    provider._agent_sub = mock_agent_sub
    
    # Exercise health check (aggregates everything)
    health = await provider.health_check()
    assert health is not None
    assert health.status == HealthStatus.HEALTHY
    
    # Exercise chat (uses LLM)
    res = await provider.chat([{"role": "user", "content": "hi"}])
    assert res == "LLM Response"
    
    # Verify we touched multiple subsystems
    assert provider._llm_sub is not None
    assert provider._rag_sub is not None
    assert provider._agent_sub is not None
