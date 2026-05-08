"""Base class for all Lexigram search backends.

``SearchBackendBase`` extends ``AbstractReadOnlyRepository[dict, str]`` so that
any search backend can satisfy the repository protocol for document dicts.  The
``AbstractReadOnlyRepository`` primitives are implemented here by delegating to
the backend-specific ``search()`` method.  Concrete backends only need to
implement the search-specific abstract interface below.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.contracts.domain.specification import SpecificationProtocol
from lexigram.logging import get_logger
from lexigram.primitives.data import AbstractReadOnlyRepository
from lexigram.result import Result
from lexigram.search.engine import validate_search_query

logger = get_logger(__name__)


class SearchBackendBase(AbstractReadOnlyRepository[dict, str]):
    """Abstract base class for all search backends.

    Extends ``AbstractReadOnlyRepository[dict, str]`` so search backends
    satisfy the standard repository read protocol.  The repository primitives
    delegate to ``self.search()`` using ``_default_index``; subclasses may
    override them for more efficient native implementations.
    """

    def __init__(self, **config: Any):
        self.config = config
        self.strict_validation = config.get("strict_validation", True)
        # Shared lazy-client slot; subclasses must call super().__init__() before using it.
        self._client: Any = None
        # Default index used by AbstractReadOnlyRepository protocol methods.
        # Override via config key "default_index" or by setting this attribute.
        self._default_index: str = str(config.get("default_index", "default"))

    # ── AbstractReadOnlyRepository primitives ─────────────────────────────

    async def _fetch_by_id(self, entity_id: str) -> dict | None:
        """Fetch a single document by ID from the default index.

        Delegates to ``search()`` with an ``id`` equality filter.  Override in
        backends that support direct document-by-ID retrieval.
        """
        result = await self.search(
            self._default_index,
            query="",
            filters={"id": str(entity_id)},
            limit=1,
        )
        if isinstance(result, Result):
            if result.is_err():
                return None
            response = result.unwrap()
        else:
            response = result
        return self._extract_first(response)

    async def _fetch_many(
        self,
        *,
        skip: int,
        limit: int,
        filters: dict[str, Any],
    ) -> list[dict]:
        """Fetch documents from the default index.

        Delegates to ``search()`` with the given offset/limit and attribute
        equality filters.
        """
        if limit == 0:
            return []
        result = await self.search(
            self._default_index,
            query="",
            filters=filters if filters else None,
            limit=limit,
            offset=skip,
        )
        if isinstance(result, Result):
            if result.is_err():
                return []
            response = result.unwrap()
        else:
            response = result
        return self._extract_results(response)

    async def _count(self, *, filters: dict[str, Any]) -> int:
        """Count documents in the default index matching filters.

        Uses a minimal search (limit=1) to retrieve the total hit count.
        Override for backends with a dedicated count endpoint.
        """
        result = await self.search(
            self._default_index,
            query="",
            filters=filters if filters else None,
            limit=1,
        )
        if isinstance(result, Result):
            if result.is_err():
                return 0
            response = result.unwrap()
        else:
            response = result
        return self._extract_total(response)

    async def find_by_spec(
        self,
        spec: SpecificationProtocol[dict],
    ) -> list[dict]:
        """Return documents satisfying *spec* (in-memory filter).

        Fetches all documents from the default index and applies the
        specification predicate in-process.  Override for backends that can
        translate specifications into native query expressions.
        """
        all_docs = await self._fetch_many(skip=0, limit=10_000, filters={})
        return [doc for doc in all_docs if spec.is_satisfied_by(doc)]

    # ── Response normalisation helpers ────────────────────────────────────

    @staticmethod
    def _extract_results(response: Any) -> list[dict]:
        """Extract a list of document dicts from any search response shape."""
        # SearchResponse: results is list[SearchResult], each has .data
        if hasattr(response, "results"):
            return [
                getattr(r, "data", r) if not isinstance(r, dict) else r
                for r in (response.results or [])
            ]
        # dict with "hits" (Elasticsearch style)
        if isinstance(response, dict):
            hits = response.get("hits", response.get("results", []))
            if isinstance(hits, dict):  # ES wraps hits in {"hits": [...]}
                hits = hits.get("hits", [])
            return [h.get("_source", h) if isinstance(h, dict) else h for h in hits]  # type: ignore[union-attr]
        return []

    @staticmethod
    def _extract_first(response: Any) -> dict | None:
        """Return the first document from a search response, or ``None``."""
        results = SearchBackendBase._extract_results(response)
        return results[0] if results else None

    @staticmethod
    def _extract_total(response: Any) -> int:
        """Extract the total hit count from any search response shape."""
        if hasattr(response, "total"):
            return int(response.total)
        if isinstance(response, dict):
            total = response.get("total", 0)
            if isinstance(total, dict):
                return int(total.get("value", 0))
            return int(total)
        return 0

    # ── Bulk operations ───────────────────────────────────────────────────

    async def bulk_operation(
        self,
        index: str,
        operations: list[dict[str, Any]],
        **kwargs: Any,
    ) -> Any:
        """Execute mixed index/delete operations, defaulting to sequential individual calls.

        Backends with a native bulk API (e.g. Elasticsearch, Typesense) should
        override this method to issue a single bulk request instead of N
        round-trips.  The default implementation here executes each operation
        one at a time and is intended as a correct-but-slow fallback for
        simpler backends.

        The ``operations`` list uses the same format as
        :meth:`DefaultSearchEngine.bulk_operation`::

            [
                {"operation": "index",  "id": "doc-1", "document": {...}},
                {"operation": "delete", "id": "doc-2"},
            ]

        Args:
            index: The index name.
            operations: List of operation dicts, each with an ``"operation"``
                key (``"index"`` or ``"delete"``), an ``"id"`` key, and for
                index operations a ``"document"`` key.
            **kwargs: Backend-specific options (ignored by the default
                implementation).

        Returns:
            :class:`BulkResult` summarising successful and failed operations.
        """
        # Local import avoids a circular dependency between backends and core.
        from lexigram.search.engine import BulkOperationResult, BulkResult

        successful = 0
        failed = 0
        results: list[BulkOperationResult] = []

        for op in operations:
            op_type = op.get("operation", "index")
            doc_id = str(op.get("id", ""))
            try:
                if op_type == "index":
                    doc = dict(op.get("document") or {})
                    # Ensure the document carries its ID so backends that
                    # extract it from the dict (e.g. Elasticsearch) work.
                    doc.setdefault("id", doc_id)
                    await self.index_document(index, doc, **kwargs)  # type: ignore[attr-defined]
                elif op_type == "delete":
                    # Try the standard name first, then the Meilisearch / MongoDB alias.
                    delete_fn = getattr(self, "delete_document", None) or getattr(
                        self, "delete", None
                    )
                    if delete_fn is not None:
                        await delete_fn(index, doc_id)
                successful += 1
                results.append(BulkOperationResult(success=True))
            except Exception as exc:  # noqa: BLE001 — must collect per-operation errors
                failed += 1
                results.append(BulkOperationResult(success=False, error=str(exc)))

        return BulkResult(successful=successful, failed=failed, operations=results)

    # ── Search-specific abstract interface ────────────────────────────────

    @abstractmethod
    async def _get_client(self) -> Any:
        """Get or create the backend-specific client."""

    @abstractmethod
    async def search(
        self,
        index_name: str,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        sort: list[str] | None = None,
    ) -> Any:
        """Execute a full-text search query.

        Implementations must return a ``SearchResponse`` or dict with a
        ``results`` list and ``total`` int.  Backends should return
        ``SearchResponse`` for full repository protocol support.
        """

    # ── Shared utilities ───────────────────────────────────────────────────

    async def _validate_search_params(
        self,
        index_name: str,
        query: str,
        filters: dict[str, Any] | None = None,
        sort: list[str] | None = None,
    ) -> None:
        """Validate search parameters before executing a query."""
        if not index_name or not isinstance(index_name, str):
            raise ValueError("Invalid index name")

        is_valid, error = validate_search_query(query)
        if not is_valid:
            if self.strict_validation:
                raise ValueError(f"Invalid search query: {error}")
            logger.warning(
                "Invalid search query detected but strict_validation is off: %s",
                error,
            )

        if filters and not isinstance(filters, dict):
            raise ValueError("Filters must be a dictionary")

        if sort and not isinstance(sort, list):
            raise ValueError("Sort must be a list of strings")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Return the operational health of this search backend."""
        component = self.__class__.__name__
        try:
            await self._get_client()
            return HealthCheckResult(
                component=component,
                status=HealthStatus.HEALTHY,
                details={"backend": component},
            )
        except Exception as e:
            logger.exception("Search backend health check error")
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                error=str(e),
                details={"backend": component},
            )
