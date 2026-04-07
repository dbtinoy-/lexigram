from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from lexigram.contracts import HealthCheckResult

if TYPE_CHECKING:
    from lexigram.result import Result
    from lexigram.search.exceptions import SearchError
    from lexigram.search.types import SearchResponse


@runtime_checkable
class SearchEngine(Protocol):
    """Protocol for search engine implementations.

    Defines the structural contract for all search backends. Implementations
    do not need to inherit from this class — any class providing these methods
    satisfies the protocol (structural subtyping).

    Concrete backends may still inherit from ``SearchEngine`` to signal explicit
    conformance and benefit from IDE completions.
    """

    async def index(
        self, index_name: str, documents: list[dict[str, Any]]
    ) -> Result[bool, SearchError]:
        """Index documents into the named index."""
        ...

    async def update(
        self,
        index_name: str,
        document_id: str,
        document: dict[str, Any],
    ) -> Result[bool, SearchError]:
        """Update an existing document by ID."""
        ...

    async def delete(
        self, index_name: str, document_id: str
    ) -> Result[bool, SearchError]:
        """Delete a document by ID."""
        ...

    async def search(
        self,
        index_name: str,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        sort: list[str] | None = None,
    ) -> Result[SearchResponse, SearchError]:
        """Execute a search query and return Ok(response) or Err(SearchError)."""
        ...

    async def create_index(
        self,
        index_name: str,
        settings: dict[str, Any] | None = None,
    ) -> Result[bool, SearchError]:
        """Create a new index, optionally with settings."""
        ...

    async def delete_index(self, index_name: str) -> Result[bool, SearchError]:
        """Delete an index and all its documents."""
        ...

    async def index_exists(self, index_name: str) -> Result[bool, SearchError]:
        """Check if an index exists."""
        ...

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Return the operational health of the backend."""
        ...
