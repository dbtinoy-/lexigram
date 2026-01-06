"""Tests for ObservableVectorStore additional edge cases."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.ai.observability.wrappers.observable_vector import ObservableVectorStore
from lexigram.result import Err, Ok


@pytest.fixture
def mock_tracer():
    tracer = MagicMock()
    ctx_manager = MagicMock()
    ctx_manager.__enter__.return_value = MagicMock()
    ctx_manager.__exit__.return_value = False
    tracer.trace_vector_operation.return_value = ctx_manager
    return tracer


@pytest.fixture
def mock_metrics():
    metrics = MagicMock()
    return metrics


@pytest.fixture
def mock_delegate():
    delegate = MagicMock()
    delegate.add = AsyncMock()
    delegate.search = AsyncMock()
    delegate.delete = AsyncMock()
    delegate.health_check = AsyncMock()
    return delegate


class TestObservableVectorStoreEdgeCases:
    """Additional edge case tests."""

    @pytest.mark.asyncio
    async def test_add_without_tracer(self, mock_delegate, mock_metrics):
        mock_delegate.add.return_value = Ok(["id1", "id2"])

        store = ObservableVectorStore(
            mock_delegate,
            backend="test",
            tracer=None,
            metrics=mock_metrics,
        )

        result = await store.add([{"page_content": "hello"}])

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_add_without_metrics(self, mock_delegate, mock_tracer):
        mock_delegate.add.return_value = Ok(["id1"])

        store = ObservableVectorStore(
            mock_delegate,
            backend="test",
            tracer=mock_tracer,
            metrics=None,
        )

        result = await store.add([{"page_content": "hello"}])

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_add_err_result(self, mock_delegate, mock_tracer, mock_metrics):
        from lexigram.contracts.data.vector.exceptions import VectorError

        mock_delegate.add.return_value = Err(VectorError("insert failed"))

        store = ObservableVectorStore(
            mock_delegate,
            backend="test",
            tracer=mock_tracer,
            metrics=mock_metrics,
        )

        result = await store.add([{"page_content": "hello"}])

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_search_err_result(self, mock_delegate, mock_tracer, mock_metrics):
        from lexigram.contracts.data.vector.exceptions import VectorError

        mock_delegate.search.return_value = Err(VectorError("search failed"))

        store = ObservableVectorStore(
            mock_delegate,
            backend="test",
            tracer=mock_tracer,
            metrics=mock_metrics,
        )

        result = await store.search(query="test")

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_search_with_query_vector(self, mock_delegate, mock_tracer, mock_metrics):
        mock_delegate.search.return_value = Ok([])

        store = ObservableVectorStore(
            mock_delegate,
            backend="test",
            tracer=mock_tracer,
            metrics=mock_metrics,
        )

        result = await store.search(query_vector=[0.1, 0.2, 0.3])

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_search_with_k(self, mock_delegate, mock_tracer, mock_metrics):
        mock_delegate.search.return_value = Ok([])

        store = ObservableVectorStore(
            mock_delegate,
            backend="test",
            tracer=mock_tracer,
            metrics=mock_metrics,
        )

        result = await store.search(query="test", k=5)

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_search_with_top_k(self, mock_delegate, mock_tracer, mock_metrics):
        mock_delegate.search.return_value = Ok([])

        store = ObservableVectorStore(
            mock_delegate,
            backend="test",
            tracer=mock_tracer,
            metrics=mock_metrics,
        )

        result = await store.search(query="test", top_k=10)

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_search_with_filter(self, mock_delegate, mock_tracer, mock_metrics):
        mock_delegate.search.return_value = Ok([])

        store = ObservableVectorStore(
            mock_delegate,
            backend="test",
            tracer=mock_tracer,
            metrics=mock_metrics,
        )

        result = await store.search(query="test", filter={"status": "published"})

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_delete_err_result(self, mock_delegate, mock_tracer, mock_metrics):
        from lexigram.contracts.data.vector.exceptions import VectorError

        mock_delegate.delete.return_value = Err(VectorError("delete failed"))

        store = ObservableVectorStore(
            mock_delegate,
            backend="test",
            tracer=mock_tracer,
            metrics=mock_metrics,
        )

        result = await store.delete(["id1"])

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_health_check_delegated(self, mock_delegate):
        store = ObservableVectorStore(mock_delegate, backend="test")

        await store.health_check(timeout=2.0)
        mock_delegate.health_check.assert_awaited_once_with(timeout=2.0)