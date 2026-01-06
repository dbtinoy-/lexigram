"""Additional tests for metrics decorators - edge cases."""

import pytest
from unittest.mock import MagicMock

from lexigram.ai.observability.metrics.decorators import (
    track_embedding_operation,
    track_llm_call,
    track_vector_operation,
)


class DummyUsage:
    def __init__(self, prompt_tokens=None, completion_tokens=None, total_tokens=None):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class DummyResult:
    def __init__(self, usage=None, cost=None):
        self.usage = usage
        self.cost = cost


class DummyVectorResult(list):
    pass


@pytest.fixture
def mock_metrics():
    """Mock AIMetrics instance."""
    metrics = MagicMock()
    metrics.llm_active_requests.increment = MagicMock()
    metrics.llm_active_requests.decrement = MagicMock()
    metrics.llm_tokens_total.increment = MagicMock()
    metrics.llm_cost_dollars.increment = MagicMock()
    metrics.llm_requests_total.increment = MagicMock()
    metrics.llm_duration_seconds.observe = MagicMock()

    metrics.vector_documents_total.increment = MagicMock()
    metrics.vector_operations_total.increment = MagicMock()
    metrics.vector_duration_seconds.observe = MagicMock()

    metrics.embedding_batch_size.observe = MagicMock()
    metrics.embedding_operations_total.increment = MagicMock()
    metrics.embedding_duration_seconds.observe = MagicMock()
    return metrics


@pytest.mark.asyncio
async def test_track_llm_call_result_with_partial_usage(mock_metrics):
    """Test track_llm_call handles result with partial usage attributes."""

    @track_llm_call(provider="test", model="test", metrics=mock_metrics)
    async def dummy_call():
        return DummyResult(usage=DummyUsage(total_tokens=50))

    result = await dummy_call()
    assert result.usage.total_tokens == 50

    mock_metrics.llm_tokens_total.increment.assert_called()


@pytest.mark.asyncio
async def test_track_llm_call_result_no_usage(mock_metrics):
    """Test track_llm_call handles result without usage attribute."""

    @track_llm_call(provider="test", model="test", metrics=mock_metrics)
    async def dummy_call():
        return "plain string"

    result = await dummy_call()
    assert result == "plain string"

    mock_metrics.llm_tokens_total.increment.assert_not_called()


@pytest.mark.asyncio
async def test_track_llm_call_cost_casting(mock_metrics):
    """Test cost is cast to microdollars."""

    @track_llm_call(provider="test", model="test", metrics=mock_metrics)
    async def dummy_call():
        return DummyResult(usage=DummyUsage(), cost=0.001)

    result = await dummy_call()
    mock_metrics.llm_cost_dollars.increment.assert_called_once()


@pytest.mark.asyncio
async def test_track_vector_operation_delete(mock_metrics):
    """Test track_vector_operation with delete operation."""

    @track_vector_operation(operation="delete", provider="test", metrics=mock_metrics)
    async def dummy_delete():
        return [1, 2, 3]

    result = await dummy_delete()

    mock_metrics.vector_operations_total.increment.assert_called()


@pytest.mark.asyncio
async def test_track_embedding_operation_empty_batch(mock_metrics):
    """Test track_embedding_operation with empty result."""

    @track_embedding_operation(model="test", metrics=mock_metrics)
    async def dummy_embed():
        return []

    result = await dummy_embed()

    mock_metrics.embedding_batch_size.observe.assert_called_once_with(value=0, labels={"model": "test"})


@pytest.mark.asyncio
async def test_track_embedding_operation_single_item(mock_metrics):
    """Test track_embedding_operation with single item."""

    @track_embedding_operation(model="test", metrics=mock_metrics)
    async def dummy_embed():
        return [0.1]

    result = await dummy_embed()
    assert len(result) == 1

    mock_metrics.embedding_batch_size.observe.assert_called_once_with(value=1, labels={"model": "test"})