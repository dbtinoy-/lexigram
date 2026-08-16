"""Backend-boundary guard tests for hostile filter values.

Hostile filter dicts must reach the mocked engine only as escaped,
non-altering terms — never as free grammar that could rewrite the
scoped query (filter bypass, cross-tenant disclosure).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("meilisearch")
pytest.importorskip("typesense")

from lexigram.search.backends.meilisearch import MeiliSearchBackend
from lexigram.search.backends.typesense import TypesenseBackend
from lexigram.search.config import TypesenseConfig

HOSTILE_VALUE = 'a" OR tenant_id != "" OR x="'
MEILI_EXPECTED = 'tenant_id = "a\\" OR tenant_id != \\"\\" OR x=\\""'
TYPESENSE_EXPECTED = 'tenant_id:"a\\" OR tenant_id != \\"\\" OR x=\\""'


class TestMeiliBackendFilterGuard:
    """Meili backend passes the rendered filter tree as a single param."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Mock MeiliSearch client with a recording ``index.search`` mock."""
        client = MagicMock()
        index = MagicMock()
        index.search.return_value = {"hits": [], "estimatedTotalHits": 0}
        client.index.return_value = index
        return client

    @pytest.fixture
    def backend(self, mock_client: MagicMock) -> MeiliSearchBackend:
        """Create a backend instance backed by the recording mock."""
        with patch("meilisearch.Client", return_value=mock_client):
            backend = MeiliSearchBackend(url="http://test:7700", api_key="key")
            backend._client = mock_client
            return backend

    @pytest.mark.asyncio
    async def test_hostile_value_reaches_engine_escaped(
        self, backend: MeiliSearchBackend, mock_client: MagicMock
    ) -> None:
        result = await backend.search(
            "idx", "q", filters={"tenant_id": HOSTILE_VALUE}
        )

        assert result.is_ok()
        search = mock_client.index.return_value.search
        search.assert_called_once()
        assert search.call_args.kwargs["filter"] == MEILI_EXPECTED
        assert search.call_args.kwargs["q"] == "q"


class TestTypesenseBackendFilterGuard:
    """Typesense backend passes the rendered filter_tree as ``filter_by``."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Mock Typesense client with a recording ``documents.search`` mock."""
        client = MagicMock()
        collection = MagicMock()
        collection.retrieve = AsyncMock()
        collection.documents.search = AsyncMock(
            return_value={"hits": [], "found": 0}
        )
        client.collections.__getitem__ = lambda _self, _key: collection
        return client

    @pytest.fixture
    def backend(self, mock_client: MagicMock) -> TypesenseBackend:
        """Create a backend instance backed by the recording mock."""
        with patch("typesense.Client", return_value=mock_client):
            config = TypesenseConfig(
                api_url="http://localhost:8108",
                api_key="test_key",
            )
            backend = TypesenseBackend(config)
            backend._client = mock_client
            return backend

    @pytest.mark.asyncio
    async def test_hostile_value_reaches_engine_escaped(
        self, backend: TypesenseBackend, mock_client: MagicMock
    ) -> None:
        result = await backend.search(
            "test_index", "test query", filters={"tenant_id": HOSTILE_VALUE}
        )

        assert result.is_ok()
        search = mock_client.collections["test_index"].documents.search
        search.assert_called_once()
        params = search.call_args.args[0]
        assert params["filter_by"] == TYPESENSE_EXPECTED
        assert params["q"] == "test query"
        assert params["limit"] == 20
