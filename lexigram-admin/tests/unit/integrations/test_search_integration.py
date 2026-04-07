"""Tests for SearchIntegration boot, query, and result unwrapping."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.admin.integrations.search import SearchIntegration


class TestSearchIntegrationBoot:
    """SearchIntegration.boot() stores the container for lazy resolution."""

    @pytest.fixture
    def config(self) -> MagicMock:
        cfg = MagicMock()
        cfg.enabled = True
        cfg.fallback_to_like = True
        return cfg

    @pytest.fixture
    def integration(self, config: MagicMock) -> SearchIntegration:
        return SearchIntegration(config=config)

    @pytest.mark.asyncio
    async def test_boot_stores_container(
        self, integration: SearchIntegration
    ) -> None:
        """boot() stores the container for lazy resolution."""
        container = MagicMock()
        integration._enabled = True

        await integration.boot(container)

        assert integration._container is container

    @pytest.mark.asyncio
    async def test_get_engine_fallback_to_noop_on_resolve_failure(
        self, integration: SearchIntegration
    ) -> None:
        """_get_engine() sets _NoOpSearch when container.resolve fails."""
        container = MagicMock()
        container.resolve = AsyncMock(side_effect=RuntimeError("not found"))
        integration._enabled = True
        await integration.boot(container)

        engine = await integration._get_engine()

        assert engine.__class__.__name__ == "_NoOpSearch"
        assert integration._search.__class__.__name__ == "_NoOpSearch"

    @pytest.mark.asyncio
    async def test_get_engine_resolves_search_engine(
        self, integration: SearchIntegration
    ) -> None:
        """_get_engine() resolves SearchEngine from lexigram.search.engine."""
        import sys

        if "lexigram.search" not in sys.modules:
            pytest.skip("lexigram.search is not installed")

        from lexigram.search.engine import SearchEngine

        mock_engine = MagicMock(spec=SearchEngine)
        mock_engine.search = AsyncMock()
        container = MagicMock()
        container.resolve = AsyncMock(return_value=mock_engine)
        integration._enabled = True
        await integration.boot(container)

        engine = await integration._get_engine()

        assert engine is mock_engine
        resolved_key = container.resolve.call_args[0][0]
        assert resolved_key is SearchEngine, (
            f"Expected SearchEngine, got {resolved_key}"
        )

    @pytest.mark.asyncio
    async def test_get_engine_does_not_resolve_search_engine_protocol(
        self, integration: SearchIntegration
    ) -> None:
        """_get_engine() does NOT resolve SearchEngineProtocol."""
        import sys

        if "lexigram.search" not in sys.modules:
            pytest.skip("lexigram.search is not installed")

        from lexigram.contracts.search import SearchEngineProtocol

        mock_protocol = MagicMock(spec=SearchEngineProtocol)
        container = MagicMock()
        container.resolve = AsyncMock(return_value=mock_protocol)
        integration._enabled = True
        await integration.boot(container)

        await integration._get_engine()

        resolved_key = container.resolve.call_args[0][0]
        assert resolved_key is not SearchEngineProtocol, (
            "_get_engine() should not resolve SearchEngineProtocol"
        )


class TestSearchIntegrationQuery:
    """SearchIntegration.query() must pass index and unwrap results."""

    def _make_integration(self, mock_backend: MagicMock) -> SearchIntegration:
        integration = SearchIntegration(config=MagicMock())
        integration._search = mock_backend
        integration._enabled = True
        return integration

    @pytest.mark.asyncio
    async def test_query_passes_index_and_search_params(self) -> None:
        """query() calls backend.search with index, query, limit, offset."""
        mock_backend = MagicMock()
        mock_backend.search = AsyncMock()
        mock_backend.search.return_value = {
            "results": [],
            "total": 0,
        }

        integration = self._make_integration(mock_backend)

        with patch.object(
            integration._search, "search", wraps=integration._search.search
        ) as spy:
            result = await integration.query(
                index="pets",
                query_str="labrador",
                limit=10,
                offset=0,
            )

            spy.assert_awaited_once()
            kwargs = spy.call_args.kwargs
            assert kwargs.get("index_name") == "pets" or spy.call_args[0][0] == "pets", (
                "query() must pass the index name as first positional arg or index_name kwarg"
            )

    @pytest.mark.asyncio
    async def test_query_returns_correct_dict_format(
        self,
    ) -> None:
        """query() returns dict with results list and total count."""
        mock_backend = MagicMock()
        mock_backend.search = AsyncMock()
        mock_backend.search.return_value = {
            "results": [
                {"id": "1", "name": "Buddy"},
                {"id": "2", "name": "Max"},
            ],
            "total": 2,
        }

        integration = self._make_integration(mock_backend)

        result = await integration.query(index="pets", query_str="dog")

        assert isinstance(result, dict)
        assert "results" in result
        assert "total" in result
        assert result["total"] == 2
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_query_handles_result_wrapper(self) -> None:
        """query() unwraps Result[SearchResponse, SearchError] returns."""
        mock_backend = MagicMock()
        mock_backend.search = AsyncMock()

        class FakeOk:
            def is_ok(self) -> bool:
                return True

            def unwrap(self):
                return {
                    "results": [{"id": "1", "name": "Whiskers"}],
                    "total": 1,
                }

        mock_backend.search.return_value = FakeOk()

        integration = self._make_integration(mock_backend)

        result = await integration.query(index="pets", query_str="cat")

        assert result["total"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "Whiskers"

    @pytest.mark.asyncio
    async def test_query_returns_empty_on_err(self) -> None:
        """query() returns empty dict on Err result."""
        mock_backend = MagicMock()
        mock_backend.search = AsyncMock()

        class FakeErr:
            def is_ok(self) -> bool:
                return False

        mock_backend.search.return_value = FakeErr()

        integration = self._make_integration(mock_backend)

        result = await integration.query(index="pets", query_str="fail")

        assert result == {"results": [], "total": 0}

    @pytest.mark.asyncio
    async def test_query_handles_bare_search_response(self) -> None:
        """query() handles objects with .results and .total attributes."""
        mock_backend = MagicMock()
        mock_backend.search = AsyncMock()

        class FakeResponse:
            results = [{"id": "1", "name": "Rex"}]
            total = 1

        mock_backend.search.return_value = FakeResponse()

        integration = self._make_integration(mock_backend)

        result = await integration.query(index="pets", query_str="rex")

        assert result["total"] == 1
        assert result["results"][0]["name"] == "Rex"

    @pytest.mark.asyncio
    async def test_query_uses_default_limit(self) -> None:
        """query() uses default limit=50 offset=0 when not specified."""
        mock_backend = MagicMock()
        mock_backend.search = AsyncMock()
        mock_backend.search.return_value = {"results": [], "total": 0}

        integration = self._make_integration(mock_backend)

        await integration.query(index="items", query_str="x")

        mock_backend.search.assert_awaited_once()
        call = mock_backend.search.call_args

        # Check kwargs or positional args for default values
        limit = call.kwargs.get("limit") or call.kwargs.get("size")
        offset = call.kwargs.get("offset") or call.kwargs.get("from_")
        # Check positional if keywords not set
        if limit is None:
            args = call[0] if call.args else ()
            limit = args[2] if len(args) > 2 else 50
        if offset is None:
            args = call[0] if call.args else ()
            offset = args[3] if len(args) > 3 else 0
        assert limit == 50, f"Expected limit=50, got {limit}"
        assert offset == 0, f"Expected offset=0, got {offset}"

    @pytest.mark.asyncio
    async def test_query_with_noop_gives_empty(
        self,
    ) -> None:
        """_NoOpSearch returns empty results."""
        integration = SearchIntegration(config=MagicMock())
        integration._enabled = True
        container = MagicMock()
        container.resolve = AsyncMock(side_effect=RuntimeError("not found"))
        await integration.boot(container)

        result = await integration.query(index="anything", query_str="test")

        assert result == {"results": [], "total": 0}
