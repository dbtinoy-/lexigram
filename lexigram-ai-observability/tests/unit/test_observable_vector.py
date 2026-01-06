"""Tests for ObservableVectorStore."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.ai.observability.wrappers.observable_vector import ObservableVectorStore
from lexigram.result import Err, Ok


@pytest.fixture
def mock_tracer():
    """Mock AITracer instance."""
    tracer = MagicMock()
    ctx_manager = MagicMock()
    ctx_manager.__enter__.return_value = MagicMock()
    ctx_manager.__exit__.return_value = False
    tracer.trace_vector_operation.return_value = ctx_manager
    return tracer


@pytest.fixture
def mock_metrics():
    """Mock AIMetrics instance."""
    metrics = MagicMock()
    return metrics


@pytest.fixture
def mock_delegate():
    """Mock VectorStoreProtocol."""
    delegate = MagicMock()
    delegate.add = AsyncMock()
    delegate.search = AsyncMock()
    delegate.delete = AsyncMock()
    delegate.health_check = AsyncMock()
    return delegate


@pytest.mark.asyncio
async def test_observable_vector_add_success(
    mock_delegate, mock_tracer, mock_metrics
):
    mock_delegate.add.return_value = Ok(["id1", "id2"])

    store = ObservableVectorStore(
        mock_delegate,
        backend="test_backend",
        collection="test_coll",
        tracer=mock_tracer,
        metrics=mock_metrics,
    )

    result = await store.add([{"page_content": "hello"}])

    assert result.is_ok()
    assert result.unwrap() == ["id1", "id2"]

    mock_tracer.trace_vector_operation.assert_called_once_with(
        "add", "test_backend", "test_coll"
    )
    mock_metrics.vector_operations_total.increment.assert_called()
    mock_metrics.vector_documents_total.increment.assert_called()
    mock_metrics.vector_duration_seconds.observe.assert_called()


@pytest.mark.asyncio
async def test_observable_vector_search_success(
    mock_delegate, mock_tracer, mock_metrics
):
    mock_delegate.search.return_value = Ok(["doc1", "doc2", "doc3"])

    store = ObservableVectorStore(
        mock_delegate,
        backend="test_backend",
        collection="test_coll",
        tracer=mock_tracer,
        metrics=mock_metrics,
    )

    result = await store.search(query="test", k=3)

    assert result.is_ok()
    assert result.unwrap() == ["doc1", "doc2", "doc3"]

    mock_tracer.trace_vector_operation.assert_called_once_with(
        "search", "test_backend", "test_coll"
    )
    mock_metrics.vector_operations_total.increment.assert_called()
    mock_metrics.vector_documents_total.increment.assert_called()
    mock_metrics.vector_duration_seconds.observe.assert_called()


@pytest.mark.asyncio
async def test_observable_vector_delete_success(
    mock_delegate, mock_tracer, mock_metrics
):
    mock_delegate.delete.return_value = Ok(1)

    store = ObservableVectorStore(
        mock_delegate,
        backend="test_backend",
        tracer=None,
        metrics=mock_metrics,
    )

    result = await store.delete(["id1"])

    assert result.is_ok()
    assert result.unwrap() == 1

    mock_metrics.vector_operations_total.increment.assert_called()
    mock_metrics.vector_duration_seconds.observe.assert_called()


@pytest.mark.asyncio
async def test_observable_vector_delegates(mock_delegate):
    store = ObservableVectorStore(
        mock_delegate, backend="test"
    )
    
    await store.health_check(timeout=2.0)
    mock_delegate.health_check.assert_awaited_once_with(timeout=2.0)
