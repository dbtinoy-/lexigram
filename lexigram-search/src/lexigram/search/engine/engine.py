"""Search Engine Core Interface"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from lexigram.contracts import SearchEngineProtocol
from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.result import Err, Ok, Result
from lexigram.search.exceptions import BackendError, SearchError

# Use Any aliases for internal models to avoid import-untyped noise during mypy run
IndexStats = Any
SearchConfig = Any
SearchResponse = Any


@dataclass
class BulkOperationResult:
    """Result of a single operation within a bulk request."""

    success: bool
    error: str | None = None


@dataclass
class BulkResult:
    """Aggregate result of a bulk operation.

    Attributes:
        successful: Number of operations that completed successfully.
        failed: Number of operations that failed.
        operations: Per-operation results, populated when partial failures occur.
    """

    successful: int
    failed: int
    operations: list[BulkOperationResult] = field(default_factory=list)


@dataclass
class SearchQuery:
    """Search query parameters"""

    q: str = ""
    filters: dict[str, Any] | None = None
    sort: list[dict[str, str]] | None = None
    limit: int = 20
    offset: int = 0
    fields: list[str] | None = None
    facets: list[str] | None = None
    aggregations: dict[str, Any] | None = None
    highlight: dict[str, Any] | None = None
    fuzzy_queries: list[dict[str, Any]] | None = None
    autocomplete_queries: list[dict[str, Any]] | None = None
    geo_filters: list[dict[str, Any]] | None = None


class SearchEngine(ABC):
    """Abstract search engine interface"""

    def __init__(self, backend: SearchEngineProtocol, config: SearchConfig):
        self.backend = backend
        self.config = config

    @abstractmethod
    async def search(
        self, index: str, query: SearchQuery, **kwargs: Any
    ) -> Result[SearchResponse, SearchError]:
        """Execute search query, returning Ok(response) or Err(SearchError)."""

    @abstractmethod
    async def index_document(
        self,
        index: str,
        document_id: str,
        document: dict[str, Any],
        **kwargs,
    ) -> bool:
        """Index a single document"""

    @abstractmethod
    async def index_many(
        self,
        index: str,
        documents: list[tuple[str, dict[str, Any]]],
        **kwargs,
    ) -> int:
        """Index multiple documents in a single bulk operation.

        Prefer this over N calls to :meth:`index_document` when processing
        batches of entities. Implementations should delegate to the backend's
        native bulk API to reduce per-document round-trip overhead.

        Args:
            index: The index name.
            documents: Sequence of ``(document_id, document)`` pairs.
            **kwargs: Backend-specific options forwarded to the bulk API.

        Returns:
            Number of documents successfully indexed.
        """

    @abstractmethod
    async def get_document(
        self,
        index: str,
        document_id: str,
        **kwargs,
    ) -> dict[str, Any] | None:
        """Retrieve a document by ID"""

    @abstractmethod
    async def delete_document(self, index: str, document_id: str, **kwargs) -> bool:
        """Delete a document by ID"""

    @abstractmethod
    async def bulk_operation(
        self,
        index: str,
        operations: list[dict[str, Any]],
        **kwargs,
    ) -> BulkResult:
        """Execute bulk operations"""

    @abstractmethod
    async def create_index(
        self,
        index: str,
        mappings: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
        **kwargs,
    ) -> bool:
        """Create an index"""

    @abstractmethod
    async def delete_index(self, index: str, **kwargs) -> bool:
        """Delete an index"""

    @abstractmethod
    async def index_exists(self, index: str, **kwargs) -> bool:
        """Check if index exists"""

    @abstractmethod
    async def get_index_stats(self, index: str, **kwargs) -> IndexStats:
        """Get index statistics"""

    @abstractmethod
    async def rename_index(self, source: str, target: str, **kwargs) -> bool:
        """Rename/move an index from source to target"""

    @abstractmethod
    async def refresh_index(self, index: str, **kwargs) -> bool:
        """Refresh an index"""

    @abstractmethod
    async def flush_index(self, index: str, **kwargs) -> bool:
        """Flush an index"""

    @abstractmethod
    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check backend health"""


class DefaultSearchEngine(SearchEngine):
    """Default search engine implementation"""

    async def search(
        self, index: str, query: SearchQuery, **kwargs: Any
    ) -> Result[SearchResponse, SearchError]:
        """Execute search query, returning Ok(response) or Err(SearchError).

        Args:
            index: The index name to search.
            query: Search parameters including query string, filters, and pagination.
            **kwargs: Backend-specific options forwarded to the search API.

        Returns:
            Ok(SearchResponse) on success, Err(SearchError) on failure.
        """
        try:
            query.limit = min(query.limit, self.config.max_limit)
            response = await self.backend.search(index, query, **kwargs)  # type: ignore[arg-type]
            return Ok(response)
        except SearchError as e:
            return Err(e)
        except Exception as e:  # noqa: BLE001 — search backend boundary
            return Err(SearchError(f"Search failed: {e}"))

    async def index_document(
        self,
        index: str,
        document_id: str,
        document: dict[str, Any],
        **kwargs,
    ) -> bool:
        """Index a single document"""
        try:
            await self.backend.index_document(
                document_id,
                document,
                index_name=index,
            )
            return True
        except Exception as e:
            raise BackendError(f"Document indexing failed: {e}") from e

    async def index_many(
        self,
        index: str,
        documents: list[tuple[str, dict[str, Any]]],
        **kwargs,
    ) -> int:
        """Index multiple documents using the backend's bulk operation API.

        Converts the list of ``(document_id, document)`` pairs into a bulk
        index payload and delegates to :meth:`bulk_operation`, avoiding the
        N-times-round-trip cost of individual :meth:`index_document` calls.

        Args:
            index: The index name.
            documents: Sequence of ``(document_id, document)`` pairs.
            **kwargs: Backend-specific options forwarded to :meth:`bulk_operation`.

        Returns:
            Number of documents successfully indexed.

        Raises:
            BackendError: If the bulk operation fails.
        """
        if not documents:
            return 0
        operations = [
            {"operation": "index", "id": doc_id, "document": doc}
            for doc_id, doc in documents
        ]
        try:
            result = await self.bulk_operation(index, operations, **kwargs)
            return result.successful
        except Exception as e:
            raise BackendError(f"Bulk document indexing failed: {e}") from e

    async def get_document(
        self,
        index: str,
        document_id: str,
        **kwargs,
    ) -> dict[str, Any] | None:
        """Retrieve a document by ID"""
        try:
            return await self.backend.get_document(index, document_id, **kwargs)  # type: ignore[attr-defined]
        except Exception as e:
            raise BackendError(f"Document retrieval failed: {e}") from e

    async def delete_document(self, index: str, document_id: str, **kwargs) -> bool:
        """Delete a document by ID"""
        try:
            await self.backend.delete_document(index, document_id, **kwargs)
            return True
        except Exception as e:
            raise BackendError(f"Document deletion failed: {e}") from e

    async def bulk_operation(
        self,
        index: str,
        operations: list[dict[str, Any]],
        **kwargs,
    ) -> BulkResult:
        """Execute bulk operations"""
        try:
            return await self.backend.bulk_operation(index, operations, **kwargs)  # type: ignore[attr-defined]
        except Exception as e:
            raise BackendError(f"Bulk operation failed: {e}") from e

    async def create_index(
        self,
        index: str,
        mappings: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
        **kwargs,
    ) -> bool:
        """Create an index"""
        try:
            return await self.backend.create_index(index, mappings, settings, **kwargs)  # type: ignore[attr-defined]
        except Exception as e:
            raise BackendError(f"Index creation failed: {e}") from e

    async def delete_index(self, index: str, **kwargs) -> bool:
        """Delete an index"""
        try:
            return await self.backend.delete_index(index, **kwargs)  # type: ignore[attr-defined]
        except Exception as e:
            raise BackendError(f"Index deletion failed: {e}") from e

    async def index_exists(self, index: str, **kwargs) -> bool:
        """Check if index exists"""
        try:
            return await self.backend.index_exists(index, **kwargs)  # type: ignore[attr-defined]
        except Exception as e:
            raise BackendError(f"Index existence check failed: {e}") from e

    async def get_index_stats(self, index: str, **kwargs) -> IndexStats:
        """Get index statistics"""
        try:
            return await self.backend.get_index_stats(index, **kwargs)  # type: ignore[attr-defined]
        except Exception as e:
            raise BackendError(f"Index stats retrieval failed: {e}") from e

    async def rename_index(self, source: str, target: str, **kwargs) -> bool:
        """Rename/move an index from source to target.

        This is a default implementation that copies data from source to target.
        Backends with native rename support (like Elasticsearch) should
        override this in their backend implementation.
        """
        try:
            # Default implementation: copy all documents then delete source
            # Backends with native rename should override this
            if not await self.backend.index_exists(source, **kwargs):  # type: ignore[attr-defined]
                return False

            # Get all documents from source
            # This is a naive implementation - backends should override
            result = await self.backend.search(
                source, {"query": {"match_all": {}}, "size": 10000}
            )
            if isinstance(result, dict):
                hits = result.get("hits", {}).get("hits", [])
                documents = [hit.get("_source", hit) for hit in hits]

                # Index to target
                if documents:
                    await self.backend.index_many(target, documents)  # type: ignore[arg-type]

            # Delete source
            await self.backend.delete_index(source)  # type: ignore[attr-defined]
            return True
        except Exception as e:
            raise BackendError(f"Index rename failed: {e}") from e

    async def refresh_index(self, index: str, **kwargs) -> bool:
        """Refresh an index"""
        try:
            return await self.backend.refresh_index(index, **kwargs)  # type: ignore[attr-defined]
        except Exception as e:
            raise BackendError(f"Index refresh failed: {e}") from e

    async def flush_index(self, index: str, **kwargs) -> bool:
        """Flush an index"""
        try:
            return await self.backend.flush_index(index, **kwargs)  # type: ignore[attr-defined]
        except Exception as e:
            raise BackendError(f"Index flush failed: {e}") from e

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check backend health"""
        try:
            return await self.backend.health_check()
        except (OSError, ConnectionError, RuntimeError, ValueError) as e:
            return HealthCheckResult(
                component="search-engine",
                status=HealthStatus.UNHEALTHY,
                details={"error": str(e)},
                error=str(e),
            )


@asynccontextmanager
async def search_engine_context(engine: SearchEngine) -> Any:
    """Context manager for search engine operations"""
    try:
        yield engine
    finally:
        # Cleanup if needed
        pass


__all__ = [
    "DefaultSearchEngine",
    "SearchEngine",
    "SearchQuery",
    "search_engine_context",
]
