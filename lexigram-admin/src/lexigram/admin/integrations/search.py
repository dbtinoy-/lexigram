"""Search integration — delegates resource search to a search index."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


@dataclass(frozen=True)
class SearchableSpec:
    """Specification for search-index-based resource searching.

    Attributes:
        index_name: Name of the search index (defaults to resource name).
        fields: Which fields to include in the searchable document body.
        result_limit: Max results per query.
    """

    index_name: str | None = None
    fields: tuple[str, ...] = ()
    result_limit: int = 50


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
        return {
            "status": "healthy"
            if self._search is not None and not isinstance(self._search, _NoOpSearch)
            else "noop"
        }

    async def query(
        self, index: str, query_str: str, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        engine = await self._get_engine()
        if isinstance(engine, _NoOpSearch):
            return {"results": [], "total": 0}
        result = await engine.search(
            index_name=index, query=query_str, limit=limit, offset=offset
        )
        return self._unwrap(result)

    async def _get_engine(self) -> Any:
        if self._search is not None:
            return self._search
        try:
            from lexigram.search.engine import SearchEngine

            self._search = await self._container.resolve(SearchEngine)
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
    def fallback_to_like(self) -> bool:
        return getattr(self._config, "fallback_to_like", True)


__all__ = ["SearchIntegration", "SearchableSpec"]
