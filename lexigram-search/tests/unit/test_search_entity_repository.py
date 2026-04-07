"""Unit tests for SearchEntityRepository, focusing on batch save_many()."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.search.engine import DefaultSearchEngine, SearchConfig
from lexigram.search.repository.entity_repository import SearchEntityRepository

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _Product:
    """Minimal entity for testing."""

    def __init__(self, product_id: str, name: str, price: float) -> None:
        self.id = product_id
        self.name = name
        self.price = price


class ProductRepository(SearchEntityRepository[_Product]):
    """Concrete test repository."""

    def _to_document(self, entity: _Product) -> dict[str, Any]:
        return {"id": entity.id, "name": entity.name, "price": entity.price}

    def _from_document(self, document: dict[str, Any]) -> _Product:
        return _Product(
            product_id=document["id"],
            name=document["name"],
            price=document["price"],
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_backend() -> MagicMock:
    """Mock search backend with all expected async methods."""
    backend = MagicMock()
    backend.search = AsyncMock()
    backend.index_document = AsyncMock(return_value=True)
    backend.get_document = AsyncMock()
    backend.delete_document = AsyncMock()
    backend.bulk_operation = AsyncMock()
    return backend


@pytest.fixture
def engine(mock_backend: MagicMock) -> DefaultSearchEngine:
    config = MagicMock(spec=SearchConfig)
    config.max_limit = 100
    return DefaultSearchEngine(backend=mock_backend, config=config)


@pytest.fixture
def repository(engine: DefaultSearchEngine) -> ProductRepository:
    return ProductRepository(engine=engine, index_name="products")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSearchEntityRepositorySaveMany:
    """Tests for SearchEntityRepository.save_many()."""

    @pytest.mark.asyncio
    async def test_save_many_uses_index_many_not_individual_calls(
        self,
        repository: ProductRepository,
        mock_backend: MagicMock,
    ) -> None:
        """save_many() must call bulk_operation once, not index_document N times."""
        bulk_result = MagicMock()
        bulk_result.successful = 3
        bulk_result.failed = 0
        mock_backend.bulk_operation.return_value = bulk_result

        products = [
            _Product("p1", "Alpha", 9.99),
            _Product("p2", "Beta", 19.99),
            _Product("p3", "Gamma", 29.99),
        ]
        result = await repository.save_many(products)

        assert result == products
        # bulk_operation called once (not 3 individual index_document calls)
        mock_backend.bulk_operation.assert_called_once()
        mock_backend.index_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_many_passes_correct_operations_to_bulk(
        self,
        repository: ProductRepository,
        mock_backend: MagicMock,
    ) -> None:
        """save_many() must generate correct bulk operation payloads."""
        bulk_result = MagicMock()
        bulk_result.successful = 2
        bulk_result.failed = 0
        mock_backend.bulk_operation.return_value = bulk_result

        products = [
            _Product("p1", "Alpha", 9.99),
            _Product("p2", "Beta", 19.99),
        ]
        await repository.save_many(products)

        call_args = mock_backend.bulk_operation.call_args
        ops: list[dict] = call_args[0][1]  # second positional arg is operations
        assert len(ops) == 2
        assert ops[0]["operation"] == "index"
        assert ops[0]["id"] == "p1"
        assert ops[0]["document"]["name"] == "Alpha"
        assert ops[1]["id"] == "p2"
        assert ops[1]["document"]["name"] == "Beta"

    @pytest.mark.asyncio
    async def test_save_many_empty_list_returns_immediately(
        self,
        repository: ProductRepository,
        mock_backend: MagicMock,
    ) -> None:
        """save_many() with an empty list must not call any backend method."""
        result = await repository.save_many([])

        assert result == []
        mock_backend.bulk_operation.assert_not_called()
        mock_backend.index_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_many_returns_original_entities(
        self,
        repository: ProductRepository,
        mock_backend: MagicMock,
    ) -> None:
        """save_many() must return the same entity objects it received."""
        bulk_result = MagicMock()
        bulk_result.successful = 1
        bulk_result.failed = 0
        mock_backend.bulk_operation.return_value = bulk_result

        product = _Product("p1", "Solo", 5.0)
        result = await repository.save_many([product])

        assert len(result) == 1
        assert result[0] is product
