"""MeiliSearch Backend."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result
from lexigram.search.backends.base import SearchBackendBase
from lexigram.search.backends.filters import render_filters
from lexigram.search.exceptions import SearchError
from lexigram.search.filterset import merge_filters, rule_to_filters
from lexigram.search.types import SearchResponse, SearchResult

logger = get_logger(__name__)


class MeiliSearchBackend(SearchBackendBase):
    """MeiliSearch backend."""

    def __init__(
        self,
        url: str = "http://localhost:7700",
        api_key: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.url = url
        self.api_key = api_key

    async def _get_client(self) -> Any:
        """Lazy initialization of MeiliSearch client."""
        if self._client is None:
            try:
                import meilisearch  # type: ignore[import-not-found]

                self._client = meilisearch.Client(self.url, self.api_key)
            except ImportError as e:
                raise ImportError(
                    "meilisearch package is required for MeiliSearch backend",
                ) from e
        return self._client

    async def index(
        self, index_name: str, documents: list[dict[str, Any]]
    ) -> Result[bool, SearchError]:
        """Index documents into MeiliSearch."""
        try:
            await self._validate_search_params(index_name, "dummy_query")
        except ValueError as e:
            return Err(SearchError(str(e)))

        if not index_name:
            return Err(SearchError("index_name must not be empty"))

        import asyncio

        client = await self._get_client()
        index = client.index(index_name)
        try:
            # Wrap blocking I/O in thread pool
            await asyncio.to_thread(index.add_documents, documents)
            return Ok(True)
        except (OSError, ValueError, RuntimeError, ConnectionError) as e:
            logger.debug("MeiliSearch index add failed: %s", e)
            return Err(SearchError(str(e)))

    async def update(
        self,
        index_name: str,
        document_id: str,
        document: dict[str, Any],
    ) -> Result[bool, SearchError]:
        """Update an existing document in MeiliSearch."""
        if not index_name:
            return Err(SearchError("index_name must not be empty"))
        import asyncio

        client = await self._get_client()
        index = client.index(index_name)
        try:
            await asyncio.to_thread(index.update_documents, [document])
            return Ok(True)
        except (OSError, ValueError, RuntimeError, ConnectionError) as e:
            logger.debug("MeiliSearch update failed: %s", e)
            return Err(SearchError(str(e)))

    async def delete(
        self, index_name: str, document_id: str
    ) -> Result[bool, SearchError]:
        """Delete a document from MeiliSearch by ID."""
        if not index_name:
            return Err(SearchError("index_name must not be empty"))
        import asyncio

        client = await self._get_client()
        index = client.index(index_name)
        try:
            await asyncio.to_thread(index.delete_document, document_id)
            return Ok(True)
        except (OSError, ValueError, RuntimeError, ConnectionError) as e:
            logger.debug("MeiliSearch delete failed: %s", e)
            return Err(SearchError(str(e)))

    async def index_document(
        self,
        document_id: str,
        document: dict[str, Any],
        index_name: str | None = None,
    ) -> None:
        """Index a single document conforming to ``SearchEngineProtocol``.

        Delegates to :meth:`index` with the document ID embedded in the
        document dict under the ``"id"`` key, as required by MeiliSearch.

        Args:
            document_id: Unique document identifier.
            document: Document data to index.
            index_name: Target index name.  Defaults to
                :attr:`_default_index` when ``None``.

        Raises:
            RuntimeError: If the underlying index call returns an error.
        """
        target = index_name or self._default_index
        doc = {"id": document_id, **document}
        result = await self.index(target, [doc])
        if result.is_err():
            raise RuntimeError(str(result.unwrap_err()))

    async def delete_document(
        self,
        document_id: str,
        index_name: str | None = None,
    ) -> None:
        """Delete a document conforming to ``SearchEngineProtocol``.

        Delegates to :meth:`delete`.

        Args:
            document_id: Unique document identifier to remove.
            index_name: Target index name.  Defaults to
                :attr:`_default_index` when ``None``.

        Raises:
            RuntimeError: If the underlying delete call returns an error.
        """
        target = index_name or self._default_index
        result = await self.delete(target, document_id)
        if result.is_err():
            raise RuntimeError(str(result.unwrap_err()))

    async def index_many(
        self,
        documents: list[tuple[str, dict[str, Any]]],
        index_name: str | None = None,
    ) -> None:
        """Index multiple documents conforming to ``SearchEngineProtocol``.

        Batches all ``(document_id, document)`` pairs into a single
        :meth:`index` call using MeiliSearch's native bulk add-documents API.

        Args:
            documents: Sequence of ``(document_id, document)`` pairs.
            index_name: Target index name.  Defaults to
                :attr:`_default_index` when ``None``.

        Raises:
            RuntimeError: If the underlying batch index call returns an error.
        """
        target = index_name or self._default_index
        docs = [{"id": doc_id, **doc} for doc_id, doc in documents]
        result = await self.index(target, docs)
        if result.is_err():
            raise RuntimeError(str(result.unwrap_err()))

    async def search(
        self,
        index_name: str,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        sort: list[str] | None = None,
        rule: str | None = None,
    ) -> Result[SearchResponse, SearchError]:
        """Execute a search against the MeiliSearch index.

        Args:
            index_name: Target index name.
            query: Search query string.
            filters: Canonical filter dict.
            limit: Maximum results to return.
            offset: Result offset for pagination.
            sort: Keyword-sorted list of ``field:asc|desc`` terms.
            rule: Query-builder block JSON string merged into *filters*
                with AND semantics.

        Returns:
            Ok(SearchResponse) or Err(SearchError) on backend failure.
        """
        try:
            await self._validate_search_params(index_name, query, filters, sort)
        except ValueError as e:
            return Err(SearchError(str(e)))

        client = await self._get_client()
        index = client.index(index_name)

        search_params = {"q": query, "limit": limit, "offset": offset}

        if filters or rule:
            filters = merge_filters(filters, rule_to_filters(rule))
            search_params["filter"] = render_filters("meilisearch", filters)

        if sort:
            search_params["sort"] = sort

        import asyncio

        try:
            response = await asyncio.to_thread(index.search, **search_params)
        except (OSError, ValueError, RuntimeError, ConnectionError) as e:
            logger.debug("MeiliSearch search failed: %s", e)
            return Err(SearchError(str(e)))

        results = []
        for hit in response.get("hits", []):
            results.append(
                SearchResult(
                    id=str(hit.get("id", hit.get("objectID", ""))),
                    score=hit.get("_rankingScore", 0.0),
                    data=hit,
                    highlights=hit.get("_formatted"),
                ),
            )

        return Ok(
            SearchResponse(
                results=results,
                total=response.get("estimatedTotalHits", 0),
                page=offset // limit + 1 if limit else 1,
                per_page=limit,
                query=query,
                took_ms=response.get("processingTimeMs"),
            )
        )

    async def create_index(
        self,
        index_name: str,
        settings: dict[str, Any] | None = None,
    ) -> Result[bool, SearchError]:
        """Create a new MeiliSearch index."""
        if not index_name:
            return Err(SearchError("index_name must not be empty"))
        import asyncio

        client = await self._get_client()
        try:
            await asyncio.to_thread(client.create_index, index_name, settings or {})
            return Ok(True)
        except (OSError, ValueError, RuntimeError, ConnectionError) as e:
            logger.debug("MeiliSearch create_index failed: %s", e)
            return Err(SearchError(str(e)))

    async def delete_index(self, index_name: str) -> Result[bool, SearchError]:
        """Delete a MeiliSearch index and all its documents."""
        if not index_name:
            return Err(SearchError("index_name must not be empty"))
        import asyncio

        client = await self._get_client()
        try:
            await asyncio.to_thread(client.delete_index, index_name)
            return Ok(True)
        except (OSError, ValueError, RuntimeError, ConnectionError) as e:
            logger.debug("MeiliSearch delete_index failed: %s", e)
            return Err(SearchError(str(e)))

    async def bulk_operation(
        self,
        index: str,
        operations: list[dict[str, Any]],
        **kwargs: Any,
    ) -> Any:
        """Execute bulk index/delete operations using MeiliSearch's native batch API.

        Groups all ``"index"`` operations into a single :meth:`index` call
        (``add_documents``), then processes ``"delete"`` operations individually
        via :meth:`delete`.

        Args:
            index: The MeiliSearch index name.
            operations: Mixed list of operation dicts as produced by
                :meth:`DefaultSearchEngine.index_many`.
            **kwargs: Ignored (included for interface compatibility).

        Returns:
            :class:`BulkResult` with per-operation detail.
        """
        from lexigram.search.engine import BulkOperationResult, BulkResult

        index_ops = [op for op in operations if op.get("operation", "index") == "index"]
        delete_ops = [op for op in operations if op.get("operation") == "delete"]

        successful = 0
        failed = 0
        results: list[BulkOperationResult] = []

        # ── Batch index via a single add_documents call ───────────────────
        if index_ops:
            docs: list[dict[str, Any]] = []
            for op in index_ops:
                doc = dict(op.get("document") or {})
                doc_id = str(op.get("id", ""))
                if doc_id:
                    doc["id"] = doc_id
                docs.append(doc)

            index_result = await self.index(index, docs)
            if index_result.is_ok():
                successful += len(docs)
                results.extend(BulkOperationResult(success=True) for _ in docs)
            else:
                failed += len(docs)
                results.extend(
                    BulkOperationResult(
                        success=False,
                        error=str(index_result.unwrap_err()),
                    )
                    for _ in docs
                )

        # ── Delete operations (sequential) ────────────────────────────────
        for op in delete_ops:
            doc_id = str(op.get("id", ""))
            delete_result = await self.delete(index, doc_id)
            if delete_result.is_ok():
                successful += 1
                results.append(BulkOperationResult(success=True))
            else:
                failed += 1
                results.append(
                    BulkOperationResult(
                        success=False, error=str(delete_result.unwrap_err())
                    )
                )

        return BulkResult(successful=successful, failed=failed, operations=results)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check MeiliSearch health.

        Returns:
            Structured health check result.
        """
        try:
            client = await self._get_client()
            import asyncio

            # MeiliSearch health check
            health = await asyncio.to_thread(client.health)

            # Additional version info if possible
            version = await asyncio.to_thread(client.get_version)

            return HealthCheckResult(
                component="meilisearch",
                status=HealthStatus.HEALTHY
                if health.get("status") == "available"
                else HealthStatus.UNHEALTHY,
                details={
                    "backend": "meilisearch",
                    "url": self.url,
                    "version": version.get("pkgVersion"),
                    "status": health.get("status"),
                },
            )
        except (OSError, ConnectionError, RuntimeError) as e:
            logger.debug("MeiliSearch health check failed: %s", e)
            return HealthCheckResult(
                component="meilisearch",
                status=HealthStatus.UNHEALTHY,
                error=str(e),
                details={"backend": "meilisearch", "url": self.url},
            )


__all__ = ["MeiliSearchBackend"]
