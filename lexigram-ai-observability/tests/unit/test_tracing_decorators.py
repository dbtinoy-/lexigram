"""Tests for observability tracing decorators."""

import pytest
from unittest.mock import MagicMock, patch

from lexigram.ai.observability.tracing.decorators import (
    trace_llm,
    trace_rag,
    trace_vector,
)


class DummyUsage:
    def __init__(self, prompt_tokens=10, completion_tokens=20, total_tokens=30):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class DummyResult:
    def __init__(self, content="Hello", usage=None, cost=0.01):
        self.content = content
        self.usage = usage
        self.cost = cost


class DummyVectorResultItem:
    def __init__(self, score=0.95):
        self.score = score


class DummyRagResult:
    def __init__(self, answer="Rag answer"):
        self.answer = answer


@pytest.fixture
def mock_span():
    """Mock span instance."""
    span = MagicMock()
    span.set_attribute = MagicMock()
    span.add_event = MagicMock()
    return span


@pytest.fixture
def mock_tracer(mock_span):
    """Mock AITracer instance."""
    tracer = MagicMock()
    
    # Setup context managers for the different trace methods
    ctx_manager = MagicMock()
    ctx_manager.__enter__.return_value = mock_span
    ctx_manager.__exit__.return_value = False
    
    tracer.trace_llm_call.return_value = ctx_manager
    tracer.trace_vector_operation.return_value = ctx_manager
    tracer.trace_rag_stage.return_value = ctx_manager
    
    return tracer


@pytest.mark.asyncio
async def test_trace_llm_success(mock_tracer, mock_span):
    @trace_llm(provider="test_prov", model="test_mod", tracer=mock_tracer)
    async def dummy_call():
        return DummyResult(usage=DummyUsage())

    result = await dummy_call()
    assert result.content == "Hello"

    mock_tracer.trace_llm_call.assert_called_once_with("test_prov", "test_mod")

    mock_span.set_attribute.assert_any_call("llm.tokens.total", 30)
    mock_span.set_attribute.assert_any_call("llm.tokens.prompt", 10)
    mock_span.set_attribute.assert_any_call("llm.tokens.completion", 20)
    mock_span.set_attribute.assert_any_call("llm.cost", 0.01)
    mock_span.set_attribute.assert_any_call("llm.response.length", 5)
    mock_span.set_attribute.assert_any_call("status", "success")


@pytest.mark.asyncio
async def test_trace_llm_error(mock_tracer, mock_span):
    @trace_llm(provider="test_prov", model="test_mod", tracer=mock_tracer)
    async def dummy_call():
        raise ValueError("test error")

    with pytest.raises(ValueError, match="test error"):
        await dummy_call()

    mock_span.set_attribute.assert_any_call("status", "error")
    mock_span.set_attribute.assert_any_call("error.type", "ValueError")
    mock_span.set_attribute.assert_any_call("error.message", "test error")
    mock_span.add_event.assert_called_once_with("exception", {"exception": "test error"})


@pytest.mark.asyncio
async def test_trace_vector_search(mock_tracer, mock_span):
    @trace_vector(operation="search", provider="test_prov", tracer=mock_tracer, collection="docs")
    async def dummy_search():
        return [DummyVectorResultItem(score=0.99), DummyVectorResultItem(score=0.88)]

    result = await dummy_search()
    assert len(result) == 2

    mock_tracer.trace_vector_operation.assert_called_once_with("search", "test_prov", "docs")

    mock_span.set_attribute.assert_any_call("results.count", 2)
    mock_span.set_attribute.assert_any_call("results.top_score", 0.99)
    mock_span.set_attribute.assert_any_call("status", "success")


@pytest.mark.asyncio
async def test_trace_rag_retrieval(mock_tracer, mock_span):
    @trace_rag(stage="retrieval", tracer=mock_tracer, pipeline="test_pipe")
    async def dummy_retrieve():
        return ["doc1", "doc2", "doc3"]

    result = await dummy_retrieve()
    assert len(result) == 3

    mock_tracer.trace_rag_stage.assert_called_once_with("retrieval", "test_pipe")
    mock_span.set_attribute.assert_any_call("documents.retrieved", 3)
    mock_span.set_attribute.assert_any_call("status", "success")


@pytest.mark.asyncio
async def test_trace_rag_synthesis(mock_tracer, mock_span):
    @trace_rag(stage="synthesis", tracer=mock_tracer, pipeline="test_pipe")
    async def dummy_synthesize():
        return DummyRagResult()

    result = await dummy_synthesize()
    assert result.answer == "Rag answer"

    mock_tracer.trace_rag_stage.assert_called_once_with("synthesis", "test_pipe")
    mock_span.set_attribute.assert_any_call("answer.length", len("Rag answer"))
    mock_span.set_attribute.assert_any_call("status", "success")
