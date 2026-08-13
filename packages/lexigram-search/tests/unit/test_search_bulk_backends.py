"""Unit tests for bulk_operation() on search backends.

Verifies that the N+1 fix is correct:
- SearchBackendBase provides a sequential fallback that calls index_document()/delete_document() N times.
- TypesenseBackend.bulk_operation() and ElasticsearchBackend.bulk_operation() route index
  operations through their native bulk_index(), avoiding N separate round-trips.
- MeiliSearchBackend.bulk_operation() routes index operations through index() (also native bulk).
- BulkResult carries the correct successful/failed counts and per-operation detail.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.result import Ok as result_ok
from lexigram.search.backends.elasticsearch.backend import ElasticsearchBackend
from lexigram.search.backends.meilisearch.backend import MeiliSearchBackend
from lexigram.search.backends.typesense.backend import TypesenseBackend
from lexigram.search.engine import BulkOperationResult, BulkResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _index_op(doc_id: str, document: dict[str, Any]) -> dict[str, Any]:
    return {"operation": "index", "id": doc_id, "document": document}


def _delete_op(doc_id: str) -> dict[str, Any]:
    return {"operation": "delete", "id": doc_id}


# ---------------------------------------------------------------------------
# BulkResult dataclass
# ---------------------------------------------------------------------------


class TestBulkResultDataclass:
    """BulkResult is a proper dataclass with the expected attributes."""

    def test_bulk_result_attributes(self) -> None:
        result = BulkResult(successful=3, failed=1)

        assert result.successful == 3
        assert result.failed == 1
        assert result.operations == []

    def test_bulk_result_with_operations(self) -> None:
        ops = [
            BulkOperationResult(success=True),
            BulkOperationResult(success=False, error="timeout"),
        ]
        result = BulkResult(successful=1, failed=1, operations=ops)

        assert len(result.operations) == 2
        assert result.operations[0].success is True
        assert result.operations[1].success is False
        assert result.operations[1].error == "timeout"

    def test_bulk_operation_result_defaults(self) -> None:
        item = BulkOperationResult(success=True)

        assert item.success is True
        assert item.error is None


# ---------------------------------------------------------------------------
# TypesenseBackend.bulk_operation()
# ---------------------------------------------------------------------------


class TestTypesenseBackendBulkOperation:
    """TypesenseBackend routes index ops through bulk_index() — single API call."""

    @pytest.fixture
    def backend(self):
        """TypesenseBackend with mocked bulk_index and delete_document."""
        backend = TypesenseBackend.__new__(TypesenseBackend)
        backend.config = {}
        backend.strict_validation = False
        backend._client = None
        backend._default_index = "default"
        backend.typesense_config = MagicMock()
        backend.bulk_index = AsyncMock(return_value={"indexed": 2, "errors": 0})
        backend.delete_document = AsyncMock(return_value=True)
        return backend

    @pytest.mark.asyncio
    async def test_index_ops_use_bulk_index(self, backend: TypesenseBackend) -> None:
        ops = [
            _index_op("1", {"title": "A"}),
            _index_op("2", {"title": "B"}),
        ]

        result = await backend.bulk_operation("products", ops)

        assert isinstance(result, BulkResult)
        assert result.successful == 2
        assert result.failed == 0
        # Only ONE call to the native bulk API (not N individual calls).
        backend.bulk_index.assert_called_once()
        bulk_call_docs = backend.bulk_index.call_args[0][1]
        assert len(bulk_call_docs) == 2

    @pytest.mark.asyncio
    async def test_delete_ops_are_sequential(self, backend: TypesenseBackend) -> None:
        ops = [_delete_op("d1"), _delete_op("d2")]

        result = await backend.bulk_operation("products", ops)

        assert result.successful == 2
        assert result.failed == 0
        assert backend.delete_document.call_count == 2

    @pytest.mark.asyncio
    async def test_mixed_ops_batch_index_sequential_delete(
        self, backend: TypesenseBackend
    ) -> None:
        ops = [
            _index_op("i1", {"name": "X"}),
            _index_op("i2", {"name": "Y"}),
            _delete_op("d1"),
        ]

        result = await backend.bulk_operation("products", ops)

        # bulk_index called ONCE for both index ops.
        backend.bulk_index.assert_called_once()
        # delete_document called once for the delete op.
        backend.delete_document.assert_called_once_with("products", "d1")
        assert result.successful == 3
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_empty_ops_returns_zero_counts(
        self, backend: TypesenseBackend
    ) -> None:
        result = await backend.bulk_operation("products", [])

        assert result.successful == 0
        assert result.failed == 0
        backend.bulk_index.assert_not_called()
        backend.delete_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_failure_captured_in_result(
        self, backend: TypesenseBackend
    ) -> None:
        backend.delete_document.side_effect = RuntimeError("not found")

        result = await backend.bulk_operation("idx", [_delete_op("x")])

        assert result.failed == 1
        assert result.successful == 0
        assert result.operations[0].success is False
        assert "not found" in (result.operations[0].error or "")


# ---------------------------------------------------------------------------
# ElasticsearchBackend.bulk_operation()
# ---------------------------------------------------------------------------


class TestElasticsearchBackendBulkOperation:
    """ElasticsearchBackend routes index ops through bulk_index() — single _bulk call."""

    @pytest.fixture
    def backend(self):
        """ElasticsearchBackend with mocked bulk_index and delete_document."""
        backend = ElasticsearchBackend.__new__(ElasticsearchBackend)
        backend.config = {}
        backend.strict_validation = False
        backend._client = None
        backend._default_index = "default"
        backend.es_config = MagicMock()
        backend.es_config.index_prefix = ""
        backend.bulk_index = AsyncMock(return_value={"indexed": 3, "errors": 0})
        backend.delete_document = AsyncMock(return_value=True)
        return backend

    @pytest.mark.asyncio
    async def test_index_ops_use_bulk_index(
        self, backend: ElasticsearchBackend
    ) -> None:
        ops = [
            _index_op("a", {"body": "text"}),
            _index_op("b", {"body": "content"}),
            _index_op("c", {"body": "data"}),
        ]

        result = await backend.bulk_operation("articles", ops)

        assert isinstance(result, BulkResult)
        assert result.successful == 3
        assert result.failed == 0
        # One _bulk call, not three individual index calls.
        backend.bulk_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_ops_are_sequential(
        self, backend: ElasticsearchBackend
    ) -> None:
        result = await backend.bulk_operation(
            "articles", [_delete_op("x"), _delete_op("y")]
        )

        assert result.successful == 2
        assert backend.delete_document.call_count == 2

    @pytest.mark.asyncio
    async def test_partial_bulk_failure_reflected(
        self, backend: ElasticsearchBackend
    ) -> None:
        # bulk_index reports 2 indexed, 1 error out of 3 documents.
        backend.bulk_index.return_value = {"indexed": 2, "errors": 1}

        ops = [_index_op(str(i), {"v": i}) for i in range(3)]
        result = await backend.bulk_operation("idx", ops)

        assert result.successful == 2
        assert result.failed == 1


# ---------------------------------------------------------------------------
# MeiliSearchBackend.bulk_operation()
# ---------------------------------------------------------------------------


class TestMeiliSearchBackendBulkOperation:
    """MeiliSearchBackend routes index ops through index() (add_documents) — native bulk."""

    @pytest.fixture
    def backend(self):
        """MeiliSearchBackend with mocked index and delete methods."""
        backend = MeiliSearchBackend.__new__(MeiliSearchBackend)
        backend.config = {}
        backend.strict_validation = False
        backend._client = None
        backend._default_index = "default"
        backend.url = "http://localhost:7700"
        backend.index = AsyncMock(return_value=result_ok(True))
        backend.delete = AsyncMock(return_value=result_ok(True))
        return backend

    @pytest.mark.asyncio
    async def test_index_ops_use_native_add_documents(
        self, backend: MeiliSearchBackend
    ) -> None:
        ops = [_index_op("p1", {"name": "X"}), _index_op("p2", {"name": "Y"})]

        result = await backend.bulk_operation("products", ops)

        assert result.successful == 2
        assert result.failed == 0
        # ONE add_documents call (not two individual inserts).
        backend.index.assert_called_once()
        docs_arg = backend.index.call_args[0][1]
        assert len(docs_arg) == 2

    @pytest.mark.asyncio
    async def test_delete_ops_call_delete(self, backend: MeiliSearchBackend) -> None:
        result = await backend.bulk_operation("products", [_delete_op("id1")])

        assert result.successful == 1
        backend.delete.assert_called_once_with("products", "id1")
