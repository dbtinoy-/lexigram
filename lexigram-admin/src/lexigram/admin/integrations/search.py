"""Search integration — delegates resource search to a search index."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

from lexigram.contracts.search import SearchEngineProtocol


class _NoOpSearch:
    async def search(
        self, index_name: str, query: str, **kwargs: Any
    ) -> dict[str, Any]:
        return {"results": [], "total": 0}


class SearchIntegration:
    """Adapter that routes list queries through a search index.

    Gracefully no-ops when ``lexigram-search`` is not installed or the
    integration is disabled.
    """

    def __init__(self, config: Any) -> None:
        self._config = config
        self._search: Any = None
        self._enabled = False

    def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.admin.config import SearchIntegrationConfig
        from lexigram.admin.integrations._optional import is_installed

        cfg = self._config
        if not isinstance(cfg, SearchIntegrationConfig):
            cfg = SearchIntegrationConfig()
        if not cfg.enabled:
            self._search = _NoOpSearch()
            return
        if not is_installed("lexigram.search"):
            self._search = _NoOpSearch()
            return
        self._enabled = True

    async def boot(self, container: ContainerResolverProtocol) -> None:
        if not self._enabled:
            return
        self._container = container

    async def shutdown(self) -> None:
        pass

    async def health_check(self) -> dict[str, Any]:
        return {"status": "healthy" if self.is_available else "noop"}

    async def query(
        self,
        index: str,
        query_str: str,
        limit: int = 50,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
        rule: str | None = None,
    ) -> dict[str, Any]:
        """Run a query against the search index.

        Args:
            index: Index name to search.
            query_str: Full-text query string.
            limit: Maximum results to return.
            offset: Result offset for pagination.
            filters: Canonical search filter dict (``{field: value}``,
                ``{field: {"op": value}}``, ``{"$or": [...]}``, ...).
            rule: Query-builder block JSON string; merged into *filters*
                with AND semantics by the engine backend.

        Returns:
            A ``{"results": [...], "total": n}`` dict.
        """
        engine = await self._get_engine()
        if isinstance(engine, _NoOpSearch):
            return {"results": [], "total": 0}
        result = await engine.search(
            index_name=index,
            query=query_str,
            filters=filters,
            rule=rule,
            limit=limit,
            offset=offset,
        )
        return self._unwrap(result)

    async def _get_engine(self) -> Any:
        if self._search is not None:
            return self._search
        try:
            self._search = await self._container.resolve(SearchEngineProtocol)
        except Exception:
            self._search = _NoOpSearch()
        return self._search

    @staticmethod
    def _unwrap(result: Any) -> dict[str, Any]:
        if hasattr(result, "is_ok"):
            if not result.is_ok():
                return {"results": [], "total": 0}
            result = result.unwrap()
        if isinstance(result, dict):
            return {
                "results": list(result.get("results", [])),
                "total": result.get("total", 0),
            }
        return {
            "results": list(result.results) if hasattr(result, "results") else [],
            "total": result.total if hasattr(result, "total") else 0,
        }

    @property
    def is_available(self) -> bool:
        """True when a real search engine is resolved (not the no-op)."""
        return self._search is not None and not isinstance(self._search, _NoOpSearch)

    @property
    def fallback_to_like(self) -> bool:
        return getattr(self._config, "fallback_to_like", True)


__all__ = ["SearchIntegration"]
