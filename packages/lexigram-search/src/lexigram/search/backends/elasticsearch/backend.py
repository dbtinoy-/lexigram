"""Elasticsearch / OpenSearch backend."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result
from lexigram.search.backends.base import SearchBackendBase
from lexigram.search.backends.filters import render_elasticsearch
from lexigram.search.config import ElasticsearchConfig
from lexigram.search.exceptions import SearchError
from lexigram.search.filterset import merge_filters, rule_to_filters
from lexigram.search.types import SearchResponse, SearchResult

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

            # Build the search query
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "title^3",
                            "name^2",
                            "description",
                            "content",
                            "text",
                            "body",
                        ],
                        "type": "best_fields",
                        "fuzziness": "AUTO",
                    },
                },
                "from": offset,
                "size": limit,
                "highlight": {
                    "fields": {
                        "title": {},
                        "description": {},
                        "content": {},
                        "body": {},
                    },
                },
            }

            # Add filters if provided
            if filters or rule:
                filters = merge_filters(filters, rule_to_filters(rule))
                filter_clauses = render_elasticsearch(filters)

                if filter_clauses:
                    search_body["query"] = {
                        "bool": {
                            "must": search_body["query"],
                            "filter": filter_clauses,
                        },
                    }

            # Execute search
            response = await self._client.search(
                index=full_index,
                body=search_body,
            )

            hits = response["hits"]["hits"]
            results = []
            for hit in hits:
                results.append(
                    SearchResult(
                        id=str(hit["_id"]),
                        score=float(hit["_score"] or 0.0),
                        data={
                            **hit["_source"],
                            "_id": hit["_id"],
                            "_score": hit["_score"],
                        },
                        highlights=hit.get("highlight"),
                    )
                )

            total = response["hits"]["total"]["value"]

            return Ok(
                SearchResponse(
                    results=results,
                    total=total,
                    page=offset // limit + 1 if limit else 1,
                    per_page=limit,
                    query=query,
                )
            )
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
        full_index = self._get_index_name(index)

        # Check if index exists
        exists = await self._client.indices.exists(index=full_index)

        if not exists:
            # Create index with mappings
            mappings = {
                "properties": {
                    "title": {"type": "text", "analyzer": "standard"},
                    "name": {"type": "text", "analyzer": "standard"},
                    "description": {"type": "text", "analyzer": "standard"},
                    "content": {"type": "text", "analyzer": "standard"},
                    "text": {"type": "text", "analyzer": "standard"},
                    "body": {"type": "text", "analyzer": "standard"},
                    "tags": {"type": "keyword"},
                    "category": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                },
            }

            settings = {
                "number_of_shards": self.es_config.number_of_shards,
                "number_of_replicas": self.es_config.number_of_replicas,
                "analysis": {
                    "analyzer": {
                        "custom_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding"],
                        },
                    },
                },
            }

            await self._client.indices.create(
                index=full_index,
                mappings=mappings,
                settings=settings,
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
        try:
            client = await self._get_client()
            info = await client.info()
            cluster_name = info.get("cluster_name", "unknown")
            version = info.get("version", {}).get("number", "unknown")
            return HealthCheckResult(
                component="elasticsearch",
                status=HealthStatus.HEALTHY,
                details={
                    "backend": "elasticsearch",
                    "cluster_name": cluster_name,
                    "version": version,
                    "hosts": self.es_config.hosts,
                },
            )
        except Exception as e:  # noqa: BLE001 — health check boundary
            logger.debug("Elasticsearch health check failed: %s", e)
            return HealthCheckResult(
                component="elasticsearch",
                status=HealthStatus.UNHEALTHY,
                error=str(e),
                details={"backend": "elasticsearch", "hosts": self.es_config.hosts},
            )

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

        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title^3",
                        "name^2",
                        "description",
                        "content",
                        "text",
                        "body",
                    ],
                },
            },
            "aggs": aggs,
            "from": offset,
            "size": limit,
        }

        response = await self._client.search(
            index=full_index,
            body=search_body,
        )

        hits = response["hits"]["hits"]
        results = [hit["_source"] for hit in hits]

        return {
            "hits": results,
            "total": response["hits"]["total"]["value"],
            "aggregations": response.get("aggregations", {}),
            "limit": limit,
            "offset": offset,
        }

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
        full_index = self._get_index_name(index)

        try:
            response = await self._client.indices.put_settings(
                index=full_index,
                body=settings,
            )
            return {"acknowledged": response.get("acknowledged", True), "index": index}
        except Exception as e:
            logger.error("update_settings_failed", index=index, error=str(e))
            raise

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
        operations = []
        for doc_id in document_ids:
            operations.append({"delete": {"_index": full_index, "_id": doc_id}})

        try:
            response = await self._client.bulk(operations=operations, **kwargs)

            # Parse response to count successes/failures
            successful = 0
            failed = 0
            errors: list[dict[str, Any]] = []

            for item in response.get("items", []):
                if "delete" in item:
                    delete_result = item["delete"]
                    if delete_result.get("status") in (200, 404):
                        # 200 = deleted, 404 = not found (still considered success)
                        successful += 1
                    else:
                        failed += 1
                        errors.append(delete_result.get("error", {}))

            return {
                "successful": successful,
                "failed": failed,
                "total": len(document_ids),
                "errors": errors if errors else None,
            }
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
        full_source = self._get_index_name(source)
        full_target = self._get_index_name(target)

        try:
            # Use reindex API to copy documents
            await self._client.reindex(
                {
                    "source": {"index": full_source},
                    "dest": {"index": full_target},
                },
                wait_for_completion=True,
            )

            # Delete the source index
            await self._client.indices.delete(index=full_source)

            return True
        except Exception as e:
            logger.error(
                "rename_index_failed",
                source=source,
                target=target,
                error=str(e),
            )
            raise


__all__ = ["ElasticsearchBackend"]
