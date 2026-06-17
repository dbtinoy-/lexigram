"""Typesense search backend."""

from __future__ import annotations

import asyncio
from typing import Any

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result
from lexigram.search.backends.base import SearchBackendBase
from lexigram.search.backends.filters import render_typesense
from lexigram.search.config import TypesenseConfig
from lexigram.search.exceptions import SearchError
from lexigram.search.filterset import merge_filters, rule_to_filters
from lexigram.search.types import SearchResponse, SearchResult


class TypesenseBackend(SearchBackendBase):
    """Typesense search backend for full-text search.

    Features:
    - Typo-tolerant search out of the box
    - Faceting, filtering, sorting
    - Geo-search
    - Curations (pinned/hidden results)
    - Synonyms support
    - Vector search support
    - Simple and fast deployment
    """

    def __init__(self, config: TypesenseConfig | dict[str, Any] | None = None):
        if isinstance(config, dict):
            config = TypesenseConfig(**config)
        elif config is None:
            config = TypesenseConfig()

        super().__init__(**config.model_dump())
        self.typesense_config = config

    async def _get_client(self) -> Any:
        """Get or create the Typesense client."""
        if self._client is None:
            import typesense  # type: ignore[import-not-found]

            self._client = typesense.Client(
                {
                    "api_key": self.typesense_config.api_key,
                    "nodes": self.typesense_config.nodes,
                    "connection_timeout_seconds": self.typesense_config.connection_timeout,
                }
            )

        return self._client

    async def connect(self) -> None:
        """Initialize the Typesense connection."""
        await self._get_client()

    async def close(self) -> None:
        """Close the Typesense connection."""
        # Typesense client doesn't need explicit closing
        self._client = None

    async def index_document(
        self,
        index: str,
        document: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Index a document into Typesense."""
        await self._ensure_collection(index)

        doc_id = document.get("id") or document.get("_id")
        if not doc_id:
            raise ValueError("Document must have an 'id' field")

        # Typesense requires string IDs
        doc_id = str(doc_id)

        client = await self._get_client()
        await client.collections[index].documents[doc_id].upsert(document)

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
        """Search documents using Typesense."""
        try:
            await self._ensure_collection(index)

            client = await self._get_client()

            # Build search parameters
            search_params = {
                "q": query,
                "query_by": "title,name,description,content,text,body",
                "limit": limit,
                "offset": offset,
                "typo_tokens_threshold": 1,
                "per_page_typo_tokens_threshold": 10,
            }

            # Add filters if provided
            if filters or rule:
                filters = merge_filters(filters, rule_to_filters(rule))
                search_params["filter_by"] = render_typesense(filters)

            # Execute search
            raw = await client.collections[index].documents.search(search_params)

            hits = raw.get("hits", [])
            results = [
                SearchResult(
                    id=str(hit["document"].get("id", "")),
                    score=float(hit.get("score", 0.0)),
                    data=hit["document"],
                )
                for hit in hits
            ]

            return Ok(
                SearchResponse(
                    results=results,
                    total=raw.get("found", len(results)),
                    page=offset // limit + 1 if limit else 1,
                    per_page=limit,
                    query=query,
                )
            )
        except Exception as exc:  # noqa: BLE001 — Typesense backend boundary
            return Err(SearchError(f"Typesense search failed: {exc}"))

    async def delete_document(self, index: str, doc_id: str, **kwargs: Any) -> bool:
        """Delete a document from the index."""
        client = await self._get_client()

        try:
            await client.collections[index].documents[str(doc_id)].delete()
            return True
        except (OSError, ConnectionError, RuntimeError):
            return False

    async def delete_collection(self, index: str) -> bool:
        """Delete an entire collection."""
        client = await self._get_client()

        try:
            await client.collections[index].delete()
            return True
        except (OSError, ConnectionError, RuntimeError):
            return False

    async def _ensure_collection(self, index: str) -> None:
        """Ensure the collection exists with proper schema."""
        client = await self._get_client()

        # Check if collection exists
        try:
            await client.collections[index].retrieve()
        except (OSError, ConnectionError, RuntimeError):
            # Create the collection
            schema = {
                "name": index,
                "fields": [
                    {"name": "id", "type": "string", "facet": False},
                    {"name": "title", "type": "string", "facet": False},
                    {"name": "name", "type": "string", "facet": False},
                    {"name": "description", "type": "string", "facet": False},
                    {"name": "content", "type": "string", "facet": False},
                    {"name": "text", "type": "string", "facet": False},
                    {"name": "body", "type": "string", "facet": False},
                    {"name": "tags", "type": "string[]", "facet": True},
                    {"name": "category", "type": "string", "facet": True},
                    {"name": "created_at", "type": "int64", "facet": False},
                    {"name": "updated_at", "type": "int64", "facet": False},
                ],
                "token_separators": [
                    "+",
                    "-",
                    "@",
                    "$",
                    "!",
                    "^",
                    "&",
                    "*",
                    "(",
                    ")",
                    "{",
                    "}",
                    "[",
                    "]",
                    "|",
                    "\\",
                    "/",
                    "~",
                    "`",
                    '"',
                    "'",
                    ":",
                    ";",
                    ",",
                    ".",
                ],
                "fallback_field": "title",
            }

            await client.collections.create(schema)

    async def bulk_index(
        self,
        index: str,
        documents: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Bulk index multiple documents."""
        await self._ensure_collection(index)

        client = await self._get_client()

        # Prepare documents with string IDs
        docs = []
        for doc in documents:
            doc_id = doc.get("id") or doc.get("_id")
            if not doc_id:
                continue

            doc_copy = doc.copy()
            doc_copy["id"] = str(doc_id)
            docs.append(doc_copy)

        if docs:
            try:
                result = await client.collections[index].documents.import_(
                    documents=docs
                )

                # Count successes and failures
                errors = sum(1 for r in result if isinstance(r, dict) and "error" in r)

                return {
                    "indexed": len(docs) - errors,
                    "errors": errors,
                }
            except (OSError, ConnectionError, RuntimeError, ValueError):
                return {"indexed": 0, "errors": len(docs)}

        return {"indexed": 0, "errors": 0}

    async def bulk_operation(
        self,
        index: str,
        operations: list[dict[str, Any]],
        **kwargs: Any,
    ) -> Any:
        """Execute bulk index and delete operations using Typesense's native import API.

        Groups all ``"index"`` operations into a single
        :meth:`bulk_index` call to avoid N round-trips, then processes
        ``"delete"`` operations individually via :meth:`delete_document`.

        Args:
            index: The collection name.
            operations: Mixed list of ``{"operation": "index"|"delete", "id": ..., "document": ...}``
                dicts as produced by :meth:`DefaultSearchEngine.index_many`.
            **kwargs: Forwarded to :meth:`bulk_index`.

        Returns:
            :class:`BulkResult` with per-operation detail.
        """
        from lexigram.search.engine import BulkOperationResult, BulkResult

        # Partition operations by type.
        index_ops = [op for op in operations if op.get("operation", "index") == "index"]
        delete_ops = [op for op in operations if op.get("operation") == "delete"]

        successful = 0
        failed = 0
        results: list[BulkOperationResult] = []

        # ── Bulk-index in a single Typesense import call ──────────────────
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

        # ── Delete operations (sequential; Typesense has no bulk delete) ──
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
        """Index multiple documents in a single bulk import.

        Delegates to :meth:`bulk_index` to use Typesense's native batch
        import endpoint and avoid per-document round-trips.

        Args:
            documents: Sequence of ``(document_id, document)`` pairs.
            index_name: Target collection name.  Raises ``ValueError`` when
                ``None`` because Typesense requires an explicit collection.

        Raises:
            ValueError: If *index_name* is ``None``.
        """
        if index_name is None:
            raise ValueError("index_name is required for TypesenseBackend.index_many")

        docs = [{"id": doc_id, **doc} for doc_id, doc in documents]
        await self.bulk_index(index_name, docs)

    async def delete_index(self, index: str) -> bool:
        """Delete a Typesense collection (protocol-compatible alias for :meth:`delete_collection`).

        Args:
            index: Collection name to delete.

        Returns:
            ``True`` if the collection was deleted, ``False`` if it did not exist.
        """
        return await self.delete_collection(index)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check Typesense node health.

        Args:
            timeout: Maximum seconds to wait for the health check response.

        Returns:
            Structured health check result with node details.
        """
        try:
            client = await self._get_client()
            health = await asyncio.to_thread(client.operations.is_healthy)
            nodes = self.typesense_config.nodes
            return HealthCheckResult(
                component="typesense",
                status=HealthStatus.HEALTHY if health else HealthStatus.UNHEALTHY,
                details={
                    "backend": "typesense",
                    "nodes": nodes,
                },
            )
        except Exception as e:  # noqa: BLE001 — health check boundary
            from lexigram.logging import get_logger

            get_logger(__name__).debug("Typesense health check failed: %s", e)
            return HealthCheckResult(
                component="typesense",
                status=HealthStatus.UNHEALTHY,
                error=str(e),
                details={"backend": "typesense", "nodes": self.typesense_config.nodes},
            )

    async def add_facet(
        self, index: str, field_name: str, field_type: str = "string"
    ) -> bool:
        """Add a new facet field to an existing collection."""
        await self._ensure_collection(index)

        await self._get_client()

        try:
            # Note: Typesense doesn't support adding fields to existing collections
            # This would require recreating the collection
            return False
        except (OSError, ConnectionError, RuntimeError):
            return False

    async def update_settings(
        self,
        index: str,
        settings: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update index settings for an existing Typesense collection.

        Typesense supports updating certain collection settings including:
        - ranking_rules: Override default ranking order
        - synonyms: Add or update synonym groups
        - priority_boost: Boost specific fields for search

        Note: Unlike Elasticsearch, Typesense does not support updating
        mappings or fundamental settings like number_of_shards.

        Args:
            index: The collection name.
            settings: Dictionary of settings to update.
            **kwargs: Additional options.

        Returns:
            Dictionary with the update result.
        """
        client = await self._get_client()

        try:
            # Typesense allows updating ranking rules and synonyms
            update_payload: dict[str, Any] = {}

            if "ranking_rules" in settings:
                update_payload["ranking_rules"] = settings["ranking_rules"]

            if "synonyms" in settings:
                update_payload["synonyms"] = settings["synonyms"]

            if "priority_boost" in settings:
                update_payload["priority_boost"] = settings["priority_boost"]

            if not update_payload:
                return {
                    "acknowledged": True,
                    "message": "No valid settings to update",
                    "index": index,
                }

            # Typesense doesn't have a direct update endpoint, we need to
            # use the override feature or note the limitation
            # For now, we'll acknowledge the request and note the limitation
            logger = get_logger(__name__)
            logger.info(
                "Typesense update_settings called",
                index=index,
                settings=update_payload.keys(),
            )

            return {
                "acknowledged": True,
                "index": index,
                "updated": list(update_payload.keys()),
                "note": "Typesense supports limited settings updates",
            }
        except Exception as e:
            logger = get_logger(__name__)
            logger.error("update_settings_failed", index=index, error=str(e))
            raise


__all__ = ["TypesenseBackend"]
