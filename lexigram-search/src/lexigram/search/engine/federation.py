"""Cross-index search federation for searching across multiple indices."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.search import SearchEngineProtocol

logger = get_logger(__name__)


@dataclass
class FederatedSearchResult:
    """Result from a federated search across multiple indices."""

    index_name: str
    results: list[dict[str, Any]]
    total_count: int


@dataclass
class FederatedResults:
    """Combined results from searching across multiple indices."""

    results: list[FederatedSearchResult] = field(default_factory=list)
    total_results: int = 0

    def to_combined_list(
        self,
        include_index: bool = True,
    ) -> list[dict[str, Any]]:
        """Convert federated results to a flat list.

        Args:
            include_index: Whether to include the source index in each result.

        Returns:
            Flat list of all results with optional index metadata.
        """
        combined = []
        for federated_result in self.results:
            for result in federated_result.results:
                if include_index:
                    result = dict(result)
                    result["_index"] = federated_result.index_name
                combined.append(result)
        return combined


class FederatedSearchEngine:
    """Federated search engine that searches across multiple indices.

    This class wraps a primary search engine and allows searching across
    multiple indices simultaneously, combining and ranking results.

    Example::

        # Create federated search across products and documents
        federated = FederatedSearchEngine(
            engine=search_engine,
            indices=["products", "documents"],
        )

        # Search across all indices
        results = await federated.search("laptop")
    """

    def __init__(
        self,
        engine: SearchEngineProtocol,
        indices: list[str] | None = None,
    ) -> None:
        """Initialize the federated search engine.

        Args:
            engine: The underlying search engine to use.
            indices: Optional list of indices to search. Can be overridden per-query.
        """
        self._engine = engine
        self._default_indices = indices or []

    def set_indices(self, indices: list[str]) -> None:
        """Set the default indices for federated searches.

        Args:
            indices: List of index names to search.
        """
        self._default_indices = indices

    async def search_across(
        self,
        query: str,
        indices: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        sort: list[dict[str, str]] | None = None,
        limit_per_index: int | None = None,
        total_limit: int | None = None,
    ) -> FederatedResults:
        """Search across multiple indices.

        Args:
            query: Search query string.
            indices: List of indices to search (overrides default).
            filters: Optional filters to apply to each search.
            sort: Sort specifications.
            limit_per_index: Maximum results per index.
            total_limit: Maximum total results across all indices.

        Returns:
            FederatedResults containing results from each index.
        """
        search_indices = indices or self._default_indices

        if not search_indices:
            logger.warning("federated_search_no_indices")
            return FederatedResults()

        results = FederatedResults()
        all_docs: list[tuple[str, dict[str, Any]]] = []

        # Search each index
        for index_name in search_indices:
            try:
                # Apply per-index limit
                limit = limit_per_index or total_limit or 100

                # Create index-specific filters if needed
                index_filters = self._apply_index_filter(filters, index_name)

                query_result = await self._engine.search(
                    query=query,
                    filters=index_filters,
                    sort=sort,
                    limit=limit,
                )

                federated_result = FederatedSearchResult(
                    index_name=index_name,
                    results=query_result.documents,  # type: ignore[attr-defined]
                    total_count=query_result.total,  # type: ignore[attr-defined]
                )
                results.results.append(federated_result)

                # Track documents with source
                for doc in query_result.documents:  # type: ignore[attr-defined]
                    doc_copy = dict(doc)
                    doc_copy["_index"] = index_name
                    all_docs.append((index_name, doc_copy))

            except (OSError, ConnectionError, RuntimeError, ValueError) as e:
                logger.error(
                    "federated_search_index_error",
                    index=index_name,
                    error=str(e),
                )
                continue

        # Apply total limit if specified
        if total_limit and len(all_docs) > total_limit:
            all_docs = all_docs[:total_limit]

        results.total_results = sum(r.total_count for r in results.results)

        return results

    def _apply_index_filter(
        self,
        filters: dict[str, Any] | None,
        index_name: str,
    ) -> dict[str, Any] | None:
        """Apply index-specific filtering.

        Args:
            filters: Base filters.
            index_name: Target index name.

        Returns:
            Filters with index-specific modifications.
        """
        if filters is None:
            return None

        # Make a copy to avoid modifying original
        modified = dict(filters)

        # Add index filter if supported
        # This is optional - backends that don't support it will ignore
        modified["_index"] = index_name

        return modified

    async def search_with_fallback(
        self,
        query: str,
        primary_indices: list[str],
        fallback_indices: list[str] | None = None,
        min_results: int = 1,
        **kwargs: Any,
    ) -> FederatedResults:
        """Search with fallback to secondary indices.

        Searches primary indices first, falls back to secondary indices
        if insufficient results are found.

        Args:
            query: Search query string.
            primary_indices: Primary indices to search first.
            fallback_indices: Secondary indices to search if needed.
            min_results: Minimum results required before fallback.
            **kwargs: Additional search parameters.

        Returns:
            FederatedResults with combined results.
        """
        # Search primary indices
        results = await self.search_across(
            query=query,
            indices=primary_indices,
            **kwargs,
        )

        # Check if we need fallback
        if results.total_results >= min_results or not fallback_indices:
            return results

        # Search fallback indices
        fallback_results = await self.search_across(
            query=query,
            indices=fallback_indices,
            **kwargs,
        )

        # Combine results
        results.results.extend(fallback_results.results)
        results.total_results += fallback_results.total_results

        return results


__all__ = [
    "FederatedResults",
    "FederatedSearchEngine",
    "FederatedSearchResult",
]
