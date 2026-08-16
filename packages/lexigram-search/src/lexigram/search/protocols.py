"""Search protocols — structural contracts for the search domain.

These Protocols define service boundaries that downstream packages can
depend on without importing concrete implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from lexigram.contracts import HealthCheckResult
from lexigram.search.types import SearchQuery, SearchResponse

if TYPE_CHECKING:
    from lexigram.result import Result
    from lexigram.search.exceptions import SearchError


@runtime_checkable
class SearchBackend(Protocol):
    """Structural contract for search backend implementations.

    Any object implementing the listed methods satisfies this protocol,
    regardless of inheritance. This allows third-party backends that do not
    subclass ``SearchEngine`` to be used transparently via the container.
    """

    async def index(
        self, index_name: str, documents: list[dict[str, Any]]
    ) -> Result[bool, SearchError]:
        """Index one or more documents into ``index_name``."""
        ...

    async def search(
        self,
        index_name: str,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Result[SearchResponse, SearchError]:
        """Execute a search query and return results."""
        ...

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Return the operational health of this backend."""
        ...


@runtime_checkable
class Indexer(Protocol):
    """Structural contract for document indexers.

    Responsible for managing the indexing lifecycle (create, update, delete)
    independently of query execution.
    """

    async def create_index(
        self,
        index_name: str,
        settings: dict[str, Any] | None = None,
    ) -> Result[bool, SearchError]:
        """Create a new index with optional settings."""
        ...

    async def delete_index(self, index_name: str) -> Result[bool, SearchError]:
        """Delete an index and all its documents."""
        ...

    async def delete(
        self, index_name: str, document_id: str
    ) -> Result[bool, SearchError]:
        """Remove a single document by ID."""
        ...

    async def update(
        self,
        index_name: str,
        document_id: str,
        document: dict[str, Any],
    ) -> Result[bool, SearchError]:
        """Replace a document's content by ID."""
        ...


@runtime_checkable
class QueryBuilder(Protocol):
    """Structural contract for query builders."""

    def build(self, query: SearchQuery) -> dict[str, Any]:
        """Convert a ``SearchQuery`` into a backend-native query representation."""
        ...


__all__ = [
    "Indexer",
    "QueryBuilder",
    "SearchBackend",
]
