"""Unit tests for OpenSearch search backend.

``opensearch-py`` may not be installed in the development environment.  We
inject a lightweight mock into ``sys.modules`` before any import so that:

* :func:`pytest.importorskip` always passes (the mock is visible as a real
  module to the import machinery).
* :class:`OpenSearchBackend` can be instantiated without the real SDK.
* Individual tests set ``backend._client = mock_client`` directly, so
  ``_get_client`` — the only place that touches ``opensearchpy`` — is never
  invoked during the test suite.
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Inject mock opensearch-py into sys.modules so the backend module and
# pytest.importorskip both succeed regardless of whether the SDK is installed.
# ---------------------------------------------------------------------------
if "opensearchpy" not in sys.modules:
    _mock_opensearch_module = MagicMock()
    _mock_opensearch_module.AsyncOpenSearch = MagicMock
    sys.modules["opensearchpy"] = _mock_opensearch_module

pytest.importorskip("opensearchpy")

from lexigram.search.backends.opensearch import OpenSearchBackend  # noqa: E402
from lexigram.search.config import OpenSearchConfig  # noqa: E402
from lexigram.search.types import SearchResponse  # noqa: E402


class TestOpenSearchBackend:
    """Tests for OpenSearchBackend — mirrors TestElasticsearchBackend exactly."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Return a mock AsyncOpenSearch client pre-configured for all call sites."""
        client = MagicMock()

        client.search = AsyncMock(
            return_value={
                "hits": {
                    "hits": [
                        {
                            "_id": "1",
                            "_score": 0.9,
                            "_source": {"id": "1", "title": "Test 1"},
                            "highlight": {"title": ["<em>Test</em> 1"]},
                        },
                        {
                            "_id": "2",
                            "_score": 0.8,
                            "_source": {"id": "2", "title": "Test 2"},
                        },
                    ],
                    "total": {"value": 2},
                }
            }
        )

        client.index = AsyncMock()
        client.delete = AsyncMock()
        client.indices.exists = AsyncMock(return_value=True)
        client.indices.create = AsyncMock()

        return client

    @pytest.fixture
    def backend(self, mock_client: MagicMock) -> OpenSearchBackend:
        """Create an OpenSearchBackend with the opensearch-py import mocked out."""
        with patch.dict(
            sys.modules,
            {"opensearchpy": sys.modules["opensearchpy"]},
        ):
            config = OpenSearchConfig(
                hosts=["http://localhost:9200"],
                index_prefix="test_",
            )
            instance = OpenSearchBackend(config)
            instance._client = mock_client
            return instance

    # ── index_document ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_index_document(
        self, backend: OpenSearchBackend, mock_client: MagicMock
    ) -> None:
        """Indexing a document returns ``{"id": ..., "status": "indexed"}``."""
        result = await backend.index_document(
            "test_index",
            {"id": "1", "title": "Test Document", "content": "test content"},
        )

        assert result["id"] == "1"
        assert result["status"] == "indexed"

    # ── search ────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_search(
        self, backend: OpenSearchBackend, mock_client: MagicMock
    ) -> None:
        """Successful search returns ``Ok(SearchResponse)``."""
        result = await backend.search("test_index", "test query", limit=10)

        assert result.is_ok()
        response = result.unwrap()
        assert isinstance(response, SearchResponse)
        assert len(response.results) == 2
        assert response.results[0].id == "1"
        assert response.results[0].score == 0.9
        assert response.total == 2

    @pytest.mark.asyncio
    async def test_search_with_filters(
        self, backend: OpenSearchBackend, mock_client: MagicMock
    ) -> None:
        """Search with filters returns ``Ok(SearchResponse)``."""
        result = await backend.search(
            "test_index",
            "test query",
            filters={"category": "tech"},
            limit=10,
        )

        assert result.is_ok()
        response = result.unwrap()
        assert len(response.results) == 2

    @pytest.mark.asyncio
    async def test_search_returns_err_on_backend_failure(
        self, backend: OpenSearchBackend, mock_client: MagicMock
    ) -> None:
        """When the client raises, search returns ``Err(SearchError)``."""
        from lexigram.search.exceptions import SearchError

        mock_client.search.side_effect = RuntimeError("connection refused")

        result = await backend.search("test_index", "test query")

        assert result.is_err()
        assert isinstance(result.unwrap_err(), SearchError)

    # ── delete_document ───────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_delete_document(
        self, backend: OpenSearchBackend, mock_client: MagicMock
    ) -> None:
        """Deleting an existing document returns ``True``."""
        result = await backend.delete_document("test_index", "1")

        assert result is True

    # ── bulk_index ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_bulk_index(
        self, backend: OpenSearchBackend, mock_client: MagicMock
    ) -> None:
        """Bulk indexing returns the correct indexed count."""
        mock_client.bulk = AsyncMock(
            return_value={
                "errors": False,
                "items": [{"index": {"status": 201}}],
            }
        )

        result = await backend.bulk_index(
            "test_index",
            [
                {"id": "1", "title": "Test 1"},
                {"id": "2", "title": "Test 2"},
            ],
        )

        assert result["indexed"] == 2
