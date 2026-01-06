"""Tests for LLMRouter LLMClientProtocol support."""

from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.serialization import dumps_str

from lexigram.ai.rag.routing.strategies.llm import LLMRouter
from lexigram.ai.rag.routing.types import DataSource, DataSourceType, QueryFeatures, QueryIntent
from lexigram.contracts.ai import LLMClientProtocol

@pytest.mark.asyncio
async def test_llm_router_with_client():
    """Test LLMRouter with platform LLMClientProtocol."""
    # Mock LLMClientProtocol
    mock_client = MagicMock(spec=LLMClientProtocol)
    
    # Mock response object
    mock_response = MagicMock()
    mock_response.content = dumps_str({
        "data_source_names": ["vec"],
        "strategy": "dense",
        "confidence": 0.9,
        "reasoning": "LLM client decision"
    })
    from lexigram.result import Ok
    mock_client.complete = AsyncMock(return_value=Ok(mock_response))
    
    router = LLMRouter(llm_client=mock_client)
    
    features = QueryFeatures(
        text="Test query",
        length=10,
        intent=QueryIntent.FACTUAL,
    )
    
    vector_source = DataSource(
        name="vec",
        type=DataSourceType.VECTOR_STORE,
        description="Vector store",
    )
    
    decision = await router.route(features, [vector_source])
    
    assert decision.data_sources[0] == vector_source
    assert decision.strategy == "dense"
    assert decision.confidence == 0.9
    assert "LLM client decision" in decision.reasoning
    
    # Verify client was called with messages
    mock_client.complete.assert_called_once()
    args, kwargs = mock_client.complete.call_args
    assert "messages" in kwargs
    assert len(kwargs["messages"]) == 1
    assert kwargs["messages"][0].content.startswith("You are a query routing expert")

@pytest.mark.asyncio
async def test_llm_router_fallback_to_fn():
    """Test LLMRouter fallback to llm_fn if no client."""
    mock_fn = AsyncMock(return_value=dumps_str({
        "data_source_names": ["vec"],
        "strategy": "hybrid",
        "confidence": 0.7,
        "reasoning": "LLM function decision"
    }))
    
    router = LLMRouter(llm_fn=mock_fn)
    
    features = QueryFeatures(
        text="Test query",
        length=10,
        intent=QueryIntent.FACTUAL,
    )
    
    vector_source = DataSource(
        name="vec",
        type=DataSourceType.VECTOR_STORE,
        description="Vector store",
    )
    
    decision = await router.route(features, [vector_source])
    
    assert decision.strategy == "hybrid"
    assert decision.confidence == 0.7
    assert "LLM function decision" in decision.reasoning
    mock_fn.assert_called_once()
