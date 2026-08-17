"""Tests for observability metrics decorators."""

import pytest
from unittest.mock import MagicMock

from lexigram.ai.observability.metrics.decorators import (
    track_embedding_operation,
    track_llm_call,
    track_vector_operation,
)


class DummyUsage:
    def __init__(self, prompt_tokens=10, completion_tokens=20, total_tokens=30):
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
    # Ensure nested mocks for increment/observe exist and return None
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
async def test_track_llm_call_success(mock_metrics):
    @track_llm_call(provider="test_provider", model="test_model", metrics=mock_metrics)
    async def dummy_call():
        return DummyResult(usage=DummyUsage(), cost=0.005)

    result = await dummy_call()

    assert result.cost == 0.005
    assert result.usage.total_tokens == 30

    labels = {"provider": "test_provider", "model": "test_model"}

    mock_metrics.llm_active_requests.increment.assert_called_once_with(labels=labels)
    mock_metrics.llm_active_requests.decrement.assert_called_once_with(labels=labels)

    assert mock_metrics.llm_tokens_total.increment.call_count == 3
    mock_metrics.llm_tokens_total.increment.assert_any_call(
        amount=30, labels={**labels, "type": "total"}
    )
    mock_metrics.llm_tokens_total.increment.assert_any_call(
        amount=10, labels={**labels, "type": "prompt"}
    )
    mock_metrics.llm_tokens_total.increment.assert_any_call(
        amount=20, labels={**labels, "type": "completion"}
    )

    mock_metrics.llm_cost_dollars.increment.assert_called_once()
    mock_metrics.llm_requests_total.increment.assert_called_once_with(
        labels={**labels, "status": "success"}
    )
    mock_metrics.llm_duration_seconds.observe.assert_called_once()


@pytest.mark.asyncio
async def test_track_llm_call_error(mock_metrics):
    @track_llm_call(provider="test_provider", model="test_model", metrics=mock_metrics)
    async def dummy_call():
        raise ValueError("test error")

    with pytest.raises(ValueError, match="test error"):
        await dummy_call()

    labels = {"provider": "test_provider", "model": "test_model"}

    mock_metrics.llm_active_requests.increment.assert_called_once_with(labels=labels)
    mock_metrics.llm_active_requests.decrement.assert_called_once_with(labels=labels)

    mock_metrics.llm_requests_total.increment.assert_called_once_with(
        labels={**labels, "status": "error"}
    )
    mock_metrics.llm_duration_seconds.observe.assert_called_once()


@pytest.mark.asyncio
async def test_track_llm_call_no_metrics():
    @track_llm_call(provider="test", model="test", metrics=None)
    async def dummy_call():
        return "success"

    assert await dummy_call() == "success"


@pytest.mark.asyncio
async def test_track_vector_operation_add(mock_metrics):
    @track_vector_operation(operation="add", provider="test_provider", metrics=mock_metrics)
    async def dummy_add():
        return DummyVectorResult([1, 2, 3])

    result = await dummy_add()
    assert len(result) == 3

    labels = {"operation": "add", "provider": "test_provider"}

    mock_metrics.vector_documents_total.increment.assert_called_once_with(
        amount=3, labels={**labels, "type": "added"}
    )
    mock_metrics.vector_operations_total.increment.assert_called_once_with(labels=labels)
    mock_metrics.vector_duration_seconds.observe.assert_called_once()


@pytest.mark.asyncio
async def test_track_vector_operation_search(mock_metrics):
    @track_vector_operation(operation="search", provider="test_provider", metrics=mock_metrics)
    async def dummy_search():
        return DummyVectorResult([1, 2])

    result = await dummy_search()
    assert len(result) == 2

    labels = {"operation": "search", "provider": "test_provider"}

    mock_metrics.vector_documents_total.increment.assert_called_once_with(
        amount=2, labels={**labels, "type": "retrieved"}
    )
    mock_metrics.vector_operations_total.increment.assert_called_once_with(labels=labels)
    mock_metrics.vector_duration_seconds.observe.assert_called_once()


@pytest.mark.asyncio
async def test_track_embedding_operation(mock_metrics):
    @track_embedding_operation(model="test_model", metrics=mock_metrics)
    async def dummy_embed():
        return [0.1, 0.2, 0.3, 0.4]

    result = await dummy_embed()
    assert len(result) == 4

    labels = {"model": "test_model"}

    mock_metrics.embedding_batch_size.observe.assert_called_once_with(
        value=4, labels=labels
    )
    mock_metrics.embedding_operations_total.increment.assert_called_once_with(
        labels=labels
    )
    mock_metrics.embedding_duration_seconds.observe.assert_called_once()
