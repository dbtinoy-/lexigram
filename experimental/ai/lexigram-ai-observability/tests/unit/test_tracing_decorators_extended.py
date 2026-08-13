"""Additional tests for tracing decorators - edge cases."""

import pytest
from unittest.mock import MagicMock

from lexigram.ai.observability.tracing.decorators import trace_llm, trace_vector, trace_rag


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

    ctx_manager = MagicMock()
    ctx_manager.__enter__.return_value = mock_span
    ctx_manager.__exit__.return_value = False

    tracer.trace_llm_call.return_value = ctx_manager
    tracer.trace_vector_operation.return_value = ctx_manager
    tracer.trace_rag_stage.return_value = ctx_manager

    return tracer


@pytest.mark.asyncio
async def test_trace_llm_result_without_usage(mock_tracer, mock_span):
    """Test trace_llm handles result without usage attribute."""

    @trace_llm(provider="test", model="test", tracer=mock_tracer)
    async def dummy_call():
        return DummyResult(usage=None)

    result = await dummy_call()
    assert result.content == "Hello"

    mock_span.set_attribute.assert_any_call("status", "success")


@pytest.mark.asyncio
async def test_trace_llm_result_without_cost(mock_tracer, mock_span):
    """Test trace_llm handles result without cost attribute."""

    @trace_llm(provider="test", model="test", tracer=mock_tracer)
    async def dummy_call():
        return DummyResult(usage=DummyUsage(), cost=None)

    result = await dummy_call()
    assert result is not None


@pytest.mark.asyncio
async def test_trace_llm_result_without_content(mock_tracer, mock_span):
    """Test trace_llm handles result without content attribute."""

    @trace_llm(provider="test", model="test", tracer=mock_tracer)
    async def dummy_call():
        return object()

    result = await dummy_call()
    mock_span.set_attribute.assert_any_call("status", "success")


@pytest.mark.asyncio
async def test_trace_vector_no_collection(mock_tracer, mock_span):
    """Test trace_vector works without collection specified."""

    @trace_vector(operation="delete", provider="test", tracer=mock_tracer, collection=None)
    async def dummy_delete():
        return []

    result = await dummy_delete()
    mock_tracer.trace_vector_operation.assert_called_once_with("delete", "test", None)


@pytest.mark.asyncio
async def test_trace_vector_empty_result(mock_tracer, mock_span):
    """Test trace_vector handles empty result."""

    @trace_vector(operation="search", provider="test", tracer=mock_tracer)
    async def dummy_search():
        return []

    result = await dummy_search()
    mock_span.set_attribute.assert_any_call("results.count", 0)
    mock_span.set_attribute.assert_any_call("status", "success")


@pytest.mark.asyncio
async def test_trace_vector_list_without_scores(mock_tracer, mock_span):
    """Test trace_vector handles list results without score attribute."""

    @trace_vector(operation="search", provider="test", tracer=mock_tracer)
    async def dummy_search():
        return ["item1", "item2"]

    result = await dummy_search()
    mock_span.set_attribute.assert_any_call("status", "success")


@pytest.mark.asyncio
async def test_trace_rag_retrieval_empty(mock_tracer, mock_span):
    """Test trace_rag handles empty retrieval."""

    @trace_rag(stage="retrieval", tracer=mock_tracer)
    async def dummy_retrieve():
        return []

    result = await dummy_retrieve()
    mock_span.set_attribute.assert_any_call("documents.retrieved", 0)


@pytest.mark.asyncio
async def test_trace_rag_synthesis_no_answer(mock_tracer, mock_span):
    """Test trace_rag handles synthesis without answer attribute."""

    @trace_rag(stage="synthesis", tracer=mock_tracer)
    async def dummy_synthesize():
        return object()

    result = await dummy_synthesize()
    mock_span.set_attribute.assert_any_call("status", "success")