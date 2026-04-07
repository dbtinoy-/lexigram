"""MongoDB text search backend.

Migrated to use ``DocumentStoreProtocol`` from ``lexigram-nosql``
for connection lifecycle.  Retains direct motor access for advanced
operations (``bulk_write``, ``list_indexes``, ``to_list``) where
the ``CollectionProtocol`` does not yet cover.
"""

from __future__ import annotations

from typing import Any

from lexigram.contracts.data import DocumentStoreProtocol
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result
from lexigram.search.backends.base import SearchBackendBase
from lexigram.search.config import MongoSearchConfig
from lexigram.search.exceptions import SearchError

logger = get_logger(__name__)


class MongoSearchBackend(SearchBackendBase):
    """MongoDB text search backend using $text indexes or Atlas Search.

    Uses ``DocumentStoreProtocol`` for connection lifecycle with
    collection access via ``CollectionProtocol`` for standard
    CRUD and direct motor access for advanced search operations.

    Supports:
    - Text indexes with language-specific stemming
    - $text operator with $meta: "textScore" for relevance scoring
    - Atlas Search (Lucene-based) for advanced features when use_atlas_search=True
    - Aggregation pipeline for facets and filters
    """

    def __init__(
        self,
        config: MongoSearchConfig | dict[str, Any] | None = None,
        document_store: DocumentStoreProtocol | None = None,
    ):
        if isinstance(config, dict):
            config = MongoSearchConfig(**config)
        elif config is None:
            config = MongoSearchConfig()

        super().__init__(**config.model_dump())
        self.mongodb_config = config
        self._document_store = document_store
        self._db: Any = None

    async def _get_client(self) -> Any:
        """Get or create the MongoDB client and database."""
        if self._document_store is not None:
            # Use the document store for connection lifecycle
            if not self._document_store.is_connected():
                await self._document_store.connect()
            return self._document_store

        # Fallback: create own motor client (backwards compatibility)
        if self._client is None:
            from motor.motor_asyncio import (  # type: ignore[import-not-found]
                AsyncIOMotorClient,
            )

            conn_str = str(self.mongodb_config.connection_string or "")
            if not conn_str:
                conn_str = "mongodb://localhost:27017"

            self._client = AsyncIOMotorClient(conn_str)
            db_name = self.mongodb_config.database_name or "search"
            self._db = self._client[db_name]

        return self._client

    def _get_raw_collection(self, index: str) -> Any:
        """Get a motor collection for advanced operations."""
        if self._document_store is not None:
            col = self._document_store.collection(index)
            if hasattr(col, "_col"):
                return col._col
        return self._db[index] if self._db is not None else None

    async def connect(self) -> None:
        """Initialize the MongoDB connection."""
        await self._get_client()

    async def close(self) -> None:
        """Close the MongoDB connection."""
        # Don't close the shared document store — only close our own client
        if self._client:
            self._client.close()
            self._client = None
            self._db = None

    async def index(
        self,
        index_name: str,
        documents: list[dict[str, Any]],
    ) -> Result[bool, SearchError]:
        """Index documents into MongoDB (delegates to index_document for each)."""
        try:
            for doc in documents:
                await self.index_document(index_name, doc)
            return Ok(True)
        except SearchError as e:
            return Err(e)

    async def update(
        self,
        index_name: str,
        document_id: str,
        document: dict[str, Any],
    ) -> Result[bool, SearchError]:
        """Update a document in MongoDB (delegates to index_document)."""
        try:
            document["id"] = document_id
            await self.index_document(index_name, document)
            return Ok(True)
        except SearchError as e:
            return Err(e)

    async def delete(
        self, index_name: str, document_id: str
    ) -> Result[bool, SearchError]:
        """Delete a document from MongoDB by ID."""
        try:
            result = await self.delete_document(index_name, document_id)
            return Ok(result)
        except SearchError as e:
            return Err(e)

    async def create_index(
        self,
        index_name: str,
        settings: dict[str, Any] | None = None,
    ) -> Result[bool, SearchError]:
        """Create an index in MongoDB (Atlas Search or standard text index)."""
        try:
            if self.mongodb_config.use_atlas_search:
                await self.create_atlas_search_index(index_name)
            return Ok(True)
        except SearchError as e:
            return Err(e)

    async def delete_index(self, index_name: str) -> Result[bool, SearchError]:
        """Delete a MongoDB collection (index)."""
        try:
            if self._document_store is not None:
                await self._document_store.drop_collection(index_name)
            elif self._db is not None:
                await self._db.drop_collection(index_name)
            return Ok(True)
        except SearchError as e:
            return Err(e)

    async def index_document(
        self,
        index: str,
        document: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Index a document into MongoDB."""
        await self._ensure_collection(index)

        doc_id = document.get("id") or document.get("_id")
        if not doc_id:
            raise ValueError("Document must have an 'id' field")

        searchable = self._extract_searchable_text(document)

        doc = {
            "_id": doc_id,
            "document": document,
            "_searchable": searchable,
        }

        # Use CollectionProtocol for standard operations
        if self._document_store is not None:
            col = self._document_store.collection(index)
            await col.replace_one({"_id": doc_id}, doc, upsert=True)
        else:
            collection = self._db[index]
            await collection.replace_one({"_id": doc_id}, doc, upsert=True)

        return {"id": doc_id, "status": "indexed"}

    async def search(  # type: ignore[override]
        self,
        index: str,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Search documents using MongoDB text search."""
        await self._ensure_collection(index)

        # Build the search query
        if self.mongodb_config.use_atlas_search:
            search_query = {
                "$search": {
                    "index": "default",
                    "text": {
                        "query": query,
                        "path": "_searchable",
                        "fuzzy": {"maxEdits": 2},
                    },
                },
            }
            project = {"score": {"$meta": "searchScore"}}
        else:
            search_query = {
                "$text": {"$search": query},
            }
            project = {"score": {"$meta": "textScore"}}

        pipeline: list[dict[str, Any]] = [search_query]

        if filters:
            filter_doc = self._build_filter_query(filters)
            pipeline.append({"$match": filter_doc})

        pipeline.append({"$project": {"document": 1, "score": project, "_id": 1}})

        if self.mongodb_config.use_atlas_search:
            pipeline.append({"$sort": {"score": -1}})
        else:
            pipeline.append({"$sort": {"score": {"$meta": "textScore"}}})

        pipeline.append({"$skip": offset})
        pipeline.append({"$limit": limit})

        # Execute aggregation via CollectionProtocol or raw collection
        results: list[dict[str, Any]] = []
        if self._document_store is not None:
            col = self._document_store.collection(index)
            async for row in col.aggregate(pipeline):  # type: ignore[attr-defined]
                doc = row.get("document", {})
                doc["_score"] = row.get("score", 0)
                results.append(doc)
        else:
            collection = self._db[index]
            cursor = collection.aggregate(pipeline)
            rows = await cursor.to_list(length=limit)
            for row in rows:
                doc = row.get("document", {})
                doc["_score"] = row.get("score", 0)
                results.append(doc)

        return {
            "hits": results,
            "total": len(results),
            "limit": limit,
            "offset": offset,
        }

    async def delete_document(self, index: str, doc_id: str, **kwargs: Any) -> bool:
        """Delete a document from the index."""
        await self._ensure_collection(index)

        if self._document_store is not None:
            col = self._document_store.collection(index)
            result = await col.delete_one({"_id": doc_id})
            return result.matched_count > 0

        collection = self._db[index]
        result = await collection.delete_one({"_id": doc_id})
        return result.deleted_count > 0

    async def index_many(
        self,
        documents: list[tuple[str, dict[str, Any]]],
        index: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Index multiple documents using MongoDB bulk upsert.

        Args:
            documents: Sequence of ``(document_id, document)`` pairs.
            index: Collection name; required for this backend.
        """
        if not documents:
            return
        if not index:
            raise ValueError("index name is required for MongoSearchBackend.index_many")

        await self._ensure_collection(index)

        # Bulk write requires raw motor access
        raw_col = self._get_raw_collection(index)
        if raw_col is None:
            raise RuntimeError("No collection available for bulk write")

        from pymongo import ReplaceOne  # type: ignore[import-not-found]

        ops = [
            ReplaceOne(
                {"_id": doc_id},
                {
                    "_id": doc_id,
                    "document": doc,
                    "_searchable": self._extract_searchable_text(doc),
                },
                upsert=True,
            )
            for doc_id, doc in documents
        ]
        await raw_col.bulk_write(ops, ordered=False)

    async def index_exists(self, index: str, **kwargs: Any) -> bool:
        """Check whether a MongoDB collection (index) exists.

        Args:
            index: Collection name to check.

        Returns:
            ``True`` if the collection exists.
        """
        if self._document_store is not None:
            collections = await self._document_store.list_collections()
            return index in collections
        collections = await self._db.list_collection_names()
        return index in collections

    def _extract_searchable_text(self, document: dict) -> str:
        """Extract searchable text from document."""
        text_fields = ["title", "name", "description", "content", "text", "body"]
        parts = []

        for field in text_fields:
            if document.get(field):
                parts.append(str(document[field]))

        for value in document.values():
            if isinstance(value, str) and len(value) < 200:
                parts.append(value)

        return " ".join(parts)

    def _build_filter_query(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Build MongoDB filter query from filters dict."""
        query = {}

        for key, value in filters.items():
            if isinstance(value, dict):
                query[key] = value
            elif isinstance(value, (list, tuple)):
                query[key] = {"$in": list(value)}
            elif isinstance(value, str) and "*" in value:
                regex_pattern = value.replace("*", ".*")
                query[key] = {"$regex": regex_pattern, "$options": "i"}
            else:
                query[key] = value

        return query

    async def _ensure_collection(self, index: str) -> None:
        """Ensure the collection and text index exist."""
        raw_col = self._get_raw_collection(index)
        if raw_col is None:
            return

        try:
            indexes = await raw_col.list_indexes().to_list(length=None)
            has_text_index = any("text" in idx.get("key", {}) for idx in indexes)

            if not has_text_index:
                await raw_col.create_index(
                    [("title", "text"), ("_searchable", "text")],
                    name="search_text_idx",
                    default_language="english",
                )
        except (OSError, ConnectionError, RuntimeError) as exc:
            logger.debug("index_creation_skipped", error=str(exc))

    async def create_atlas_search_index(self, index: str) -> None:
        """Create an Atlas Search index for advanced search capabilities."""
        # Atlas Search index definition
        # Note: This requires Atlas Search to be enabled


__all__ = ["MongoSearchBackend"]
