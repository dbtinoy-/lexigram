"""Elasticsearch / OpenSearch backend."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.core import HealthCheckResult
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result
from lexigram.search.backends.base import SearchBackendBase
from lexigram.search.backends.elasticsearch import health, index_mgmt, search_ops
from lexigram.search.config import ElasticsearchConfig
from lexigram.search.exceptions import SearchError
from lexigram.search.types import SearchResponse

logger = get_logger(__name__)


class ElasticsearchBackend(SearchBackendBase):
    """Elasticsearch / OpenSearch backend for full-text search.

    Features:
    - BM25 ranking (default Elasticsearch scoring)
    - Custom analyzers and tokenizers
    - Fuzzy queries, multi-match, bool queries
    - Aggregations (terms, range, date histogram, nested)
    - Highlighting with multiple strategies
    - Vector search support (dense_vector, kNN)
    - OpenSearch compatibility

    Transport groups live in sibling modules consumed by this class:
    ``search_ops`` (query building/parsing), ``index_mgmt`` (index and
    bulk management), and ``health`` (cluster health).
    """

    def __init__(self, config: ElasticsearchConfig | dict[str, Any] | None = None):
        if isinstance(config, dict):
            config = ElasticsearchConfig(**config)
        elif config is None:
            config = ElasticsearchConfig()

        super().__init__(**config.model_dump())
        self.es_config = config

    async def _get_client(self) -> Any:
        """Get or create the Elasticsearch client."""
        if self._client is None:
            from elasticsearch import (  # type: ignore[import-not-found]
                AsyncElasticsearch,
            )

            # Build connection kwargs
            kwargs: dict[str, Any] = {"hosts": self.es_config.hosts}

            if self.es_config.api_key:
                kwargs["api_key"] = (
                    self.es_config.api_key.get_secret_value()
                    if self.es_config.api_key
                    else None
                )
            elif self.es_config.username and self.es_config.password:
                kwargs["basic_auth"] = (
                    self.es_config.username,
                    self.es_config.password.get_secret_value()
                    if self.es_config.password
                    else None,
                )

            if self.es_config.use_ssl:
                kwargs["use_ssl"] = True
                kwargs["verify_certs"] = self.es_config.verify_certs

            self._client = AsyncElasticsearch(**kwargs)

        return self._client

    async def connect(self) -> None:
        """Initialize the Elasticsearch connection."""
        await self._get_client()

    async def close(self) -> None:
        """Close the Elasticsearch connection."""
        if self._client:
            await self._client.close()
            self._client = None

    def _get_index_name(self, index: str) -> str:
        """Get the full index name with prefix."""
        return f"{self.es_config.index_prefix}{index}"

    async def index_document(
        self,
        index: str,
        document: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Index a document into Elasticsearch."""
        await self._ensure_index(index)

        doc_id = document.get("id") or document.get("_id")
        if not doc_id:
            raise ValueError("Document must have an 'id' field")

        full_index = self._get_index_name(index)

        await self._client.index(
            index=full_index,
            id=doc_id,
            document=document,
            refresh=True,
        )

        return {"id": doc_id, "status": "indexed"}

    async def search(  # type: ignore[override]
        self,
        index: str,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        rule: str | None = None,
        **kwargs: Any,
    ) -> Result[SearchResponse, SearchError]:
        """Search documents using Elasticsearch."""
        try:
            await self._ensure_index(index)

            full_index = self._get_index_name(index)

            # Build the search query and apply filterset filters
            search_body = search_ops.build_search_body(query, offset, limit)
            search_ops.apply_search_filters(search_body, filters, rule)

            # Execute search
            response = await self._client.search(
                index=full_index,
                body=search_body,
            )

            return Ok(search_ops.parse_search_response(response, query, offset, limit))
        except Exception as exc:  # noqa: BLE001 — Elasticsearch backend boundary
            return Err(SearchError(f"Elasticsearch search failed: {exc}"))

    async def delete_document(self, index: str, doc_id: str, **kwargs: Any) -> bool:
        """Delete a document from the index."""
        full_index = self._get_index_name(index)

        try:
            await self._client.delete(
                index=full_index,
                id=doc_id,
                refresh=True,
            )
            return True
        except (OSError, ConnectionError, RuntimeError):
            return False

    async def delete_index(self, index: str) -> bool:
        """Delete an entire index."""
        full_index = self._get_index_name(index)

        try:
            await self._client.indices.delete(index=full_index)
            return True
        except (OSError, ConnectionError, RuntimeError):
            return False

    async def _ensure_index(self, index: str) -> None:
        """Ensure the index exists with proper mappings."""
        await index_mgmt.ensure_index(
            self._client,
            self._get_index_name(index),
            self.es_config,
        )

    async def bulk_index(
        self,
        index: str,
        documents: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Bulk index multiple documents."""
        await self._ensure_index(index)

        full_index = self._get_index_name(index)

        operations = []
        for doc in documents:
            doc_id = doc.get("id") or doc.get("_id")
            if not doc_id:
                continue

            operations.append({"index": {"_index": full_index, "_id": doc_id}})
            operations.append(doc)

        if operations:
            response = await self._client.bulk(operations=operations, refresh=True)

            errors = [op for op in response["items"] if "error" in op.get("index", {})]

            return {
                "indexed": len(operations) // 2 - len(errors),
                "errors": len(errors),
            }

        return {"indexed": 0, "errors": 0}

    async def bulk_operation(
        self,
        index: str,
        operations: list[dict[str, Any]],
        **kwargs: Any,
    ) -> Any:
        """Execute bulk index and delete operations using Elasticsearch's native bulk API.

        Groups all ``"index"`` operations into a single :meth:`bulk_index` call
        to avoid N round-trips, then processes ``"delete"`` operations
        individually via :meth:`delete_document`.

        Args:
            index: The index name.
            operations: Mixed list of ``{"operation": "index"|"delete", "id": ..., "document": ...}``
                dicts as produced by :meth:`DefaultSearchEngine.index_many`.
            **kwargs: Forwarded to :meth:`bulk_index`.

        Returns:
            :class:`BulkResult` with per-operation detail.
        """
        from lexigram.search.engine import BulkOperationResult, BulkResult

        index_ops = [op for op in operations if op.get("operation", "index") == "index"]
        delete_ops = [op for op in operations if op.get("operation") == "delete"]

        successful = 0
        failed = 0
        results: list[BulkOperationResult] = []

        # ── Bulk-index via a single Elasticsearch _bulk request ───────────
        if index_ops:
            docs: list[dict[str, Any]] = []
            for op in index_ops:
                doc = dict(op.get("document") or {})
                doc_id = str(op.get("id", ""))
                if doc_id:
                    doc["id"] = doc_id
                docs.append(doc)

            result = await self.bulk_index(index, docs, **kwargs)
            indexed = (
                result.get("indexed", 0) if isinstance(result, dict) else len(docs)
            )
            errors = result.get("errors", 0) if isinstance(result, dict) else 0
            successful += indexed
            failed += errors
            for i, _doc in enumerate(docs):
                results.append(BulkOperationResult(success=(i < indexed)))

        # ── Delete operations (sequential; ES bulk delete is less common) ─
        for op in delete_ops:
            doc_id = str(op.get("id", ""))
            try:
                await self.delete_document(index, doc_id)
                successful += 1
                results.append(BulkOperationResult(success=True))
            except Exception as exc:  # noqa: BLE001 — collect per-operation errors
                failed += 1
                results.append(BulkOperationResult(success=False, error=str(exc)))

        return BulkResult(successful=successful, failed=failed, operations=results)

    async def index_many(
        self,
        documents: list[tuple[str, dict[str, Any]]],
        index_name: str | None = None,
    ) -> None:
        """Index multiple documents in a single bulk request.

        Delegates to :meth:`bulk_index` for efficient ES bulk API usage.

        Args:
            documents: Sequence of ``(document_id, document)`` pairs.
            index_name: Target index.  Raises ``ValueError`` when ``None``
                because Elasticsearch requires an explicit index.

        Raises:
            ValueError: If *index_name* is ``None``.
        """
        if index_name is None:
            raise ValueError(
                "index_name is required for ElasticsearchBackend.index_many"
            )

        docs = [{"id": doc_id, **doc} for doc_id, doc in documents]
        await self.bulk_index(index_name, docs)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check Elasticsearch cluster health.

        Args:
            timeout: Maximum seconds to wait for the health check response.

        Returns:
            Structured health check result with cluster status details.
        """
        client = await self._get_client()
        return await health.check_cluster_health(client, self.es_config.hosts)

    async def aggregate(
        self,
        index: str,
        query: str,
        aggs: dict[str, Any],
        limit: int = 20,
        offset: int = 0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Search with aggregations (faceting)."""
        await self._ensure_index(index)

        full_index = self._get_index_name(index)

        search_body = search_ops.build_aggregate_body(query, aggs, offset, limit)

        response = await self._client.search(
            index=full_index,
            body=search_body,
        )

        return search_ops.parse_aggregate_response(response, limit, offset)

    async def update_settings(
        self,
        index: str,
        settings: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update index settings for an existing index.

        Args:
            index: The index name.
            settings: Dictionary of settings to update (e.g., number_of_replicas).
            **kwargs: Additional Elasticsearch-specific options.

        Returns:
            Dictionary with the update result.
        """
        return await index_mgmt.update_index_settings(
            self._client,
            self._get_index_name(index),
            index,
            settings,
        )

    async def bulk_delete(
        self,
        index: str,
        document_ids: list[str],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Bulk delete multiple documents by ID using Elasticsearch's bulk API.

        This is more efficient than calling delete_document() for each ID
        as it uses a single HTTP request.

        Args:
            index: The index name.
            document_ids: List of document IDs to delete.
            **kwargs: Additional options (e.g., refresh).

        Returns:
            Dictionary with the number of successful and failed deletions.
        """
        if not document_ids:
            return {"successful": 0, "failed": 0, "total": 0}

        full_index = self._get_index_name(index)

        # Build bulk delete operations
        operations = index_mgmt.build_bulk_delete_operations(full_index, document_ids)

        try:
            response = await self._client.bulk(operations=operations, **kwargs)
            return index_mgmt.parse_bulk_delete_response(response, len(document_ids))
        except Exception as e:
            logger.error("bulk_delete_failed", index=index, error=str(e))
            raise

    async def rename_index(self, source: str, target: str, **kwargs: Any) -> bool:
        """Rename an index by using the reindex API.

        Elasticsearch doesn't have a direct rename, but we can use
        the reindex API to copy from source to target, then delete source.

        Args:
            source: The source index name.
            target: The target index name.
            **kwargs: Additional options.

        Returns:
            True if successful.
        """
        return await index_mgmt.rename_index_via_reindex(
            self._client,
            self._get_index_name(source),
            self._get_index_name(target),
            source,
            target,
        )


__all__ = ["ElasticsearchBackend"]
