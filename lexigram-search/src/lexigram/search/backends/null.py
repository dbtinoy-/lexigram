"""Null search backend for testing and default fallback."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.result import Ok, Result
from lexigram.search.engine import SearchEngine, SearchResponse
from lexigram.search.exceptions import SearchError


class NullBackend(SearchEngine):
    """Search engine that does nothing (in-memory/noop)."""

    async def index(
        self, index_name: str, documents: list[dict[str, Any]]
    ) -> Result[bool, SearchError]:
        return Ok(True)

    async def update(
        self,
        index_name: str,
        document_id: str,
        document: dict[str, Any],
    ) -> Result[bool, SearchError]:
        return Ok(True)

    async def delete(
        self, index_name: str, document_id: str
    ) -> Result[bool, SearchError]:
        return Ok(True)

    async def search(
        self,
        index_name: str,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        sort: list[str] | None = None,
    ) -> Result[SearchResponse, SearchError]:
        return Ok(
            SearchResponse(
                results=[],
                total=0,
                page=offset // limit + 1 if limit else 1,
                per_page=limit,
                query=query,
                took_ms=0,
            )
        )

    async def create_index(
        self,
        index_name: str,
        settings: dict[str, Any] | None = None,
    ) -> Result[bool, SearchError]:
        return Ok(True)

    async def delete_index(self, index_name: str) -> Result[bool, SearchError]:
        return Ok(True)

    async def index_exists(self, index_name: str) -> Result[bool, SearchError]:
        return Ok(True)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        return HealthCheckResult(
            component="search",
            status=HealthStatus.HEALTHY,
            details={"backend": "NullBackend"},
        )
