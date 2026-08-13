"""Base document repository for NoSQL data access."""

from __future__ import annotations

from abc import abstractmethod
import builtins
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.data.nosql.nosql import (
        CollectionProtocol,
        DocumentStoreProtocol,
    )
    from lexigram.contracts.domain.specification import SpecificationProtocol

TEntity = TypeVar("TEntity")
TKey = TypeVar("TKey", bound=str)

logger = get_logger(__name__)


class DocumentRepository(Generic[TEntity, TKey]):
    """Base repository for document-oriented storage.

    Provides the same developer experience as ``SQLRepository`` but
    operates on documents instead of SQL rows.

    Subclasses must define:

    - ``collection_name``: the MongoDB collection name
    - ``_document_to_entity``: convert a raw dict to a domain entity
    - ``_entity_to_document``: convert a domain entity to a raw dict

    Supports soft delete and multi-tenant filtering.

    Usage::

        class UserRepository(DocumentRepository[User, str]):
            collection_name = "users"
            id_field = "_id"

            async def _document_to_entity(self, doc: dict) -> User:
                return User(**doc)

            async def _entity_to_document(self, entity: User) -> dict:
                return entity.to_dict()
    """

    collection_name: str
    id_field: str = "_id"

    def __init__(
        self,
        store: DocumentStoreProtocol,
        *,
        soft_delete: bool = False,
        multi_tenant: bool = False,
    ) -> None:
        self._store = store
        self._collection: CollectionProtocol = store.collection(self.collection_name)
        self._soft_delete = soft_delete
        self._multi_tenant = multi_tenant

    # ── Abstract methods ─────────────────────────────────────────

    @abstractmethod
    async def _document_to_entity(self, document: dict[str, Any]) -> TEntity:
        """Convert a raw document to a domain entity."""
        ...

    @abstractmethod
    async def _entity_to_document(self, entity: TEntity) -> dict[str, Any]:
        """Convert a domain entity to a raw document."""
        ...

    # ── Read operations ──────────────────────────────────────────

    async def get(self, document_id: TKey) -> TEntity | None:
        """Retrieve a document by its ID.

        Args:
            document_id: The document identifier.

        Returns:
            The entity or ``None`` if not found.
        """
        base_filter = self._base_filter()
        base_filter[self.id_field] = document_id
        doc = await self._collection.find_one(base_filter)
        if doc is None:
            return None
        return await self._document_to_entity(doc)

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        *,
        sort: builtins.list[tuple[str, int]] | None = None,
        **filters: Any,
    ) -> builtins.list[TEntity]:
        """List documents with pagination and optional filters.

        Args:
            skip: Number of documents to skip.
            limit: Maximum number of documents to return.
            sort: Sort specification as ``[(field, direction)]``.
            **filters: Keyword filters applied as equality matches.

        Returns:
            List of domain entities.
        """
        filter_dict = self._build_filter(**filters)
        entities: builtins.list[TEntity] = []
        async for doc in self._collection.find(  # type: ignore[attr-defined]
            filter_dict,
            sort=sort,
            skip=skip,
            limit=limit,
        ):
            entities.append(await self._document_to_entity(doc))
        return entities

    async def find_by_filter(self, filter: dict[str, Any]) -> builtins.list[TEntity]:
        """Find documents matching a raw filter expression.

        Args:
            filter: MongoDB-style filter dict.

        Returns:
            List of matching entities.
        """
        combined = self._base_filter()
        combined.update(filter)
        entities: builtins.list[TEntity] = []
        async for doc in self._collection.find(combined):  # type: ignore[attr-defined]
            entities.append(await self._document_to_entity(doc))
        return entities

    async def find_by_spec(
        self, spec: SpecificationProtocol[TEntity]
    ) -> builtins.list[TEntity]:
        """Find documents matching a specification.

        Converts the specification to a MongoDB filter using
        ``lexigram.nosql.specification.document.to_filter``.

        Args:
            spec: A composable filter specification.

        Returns:
            List of matching entities.
        """
        from lexigram.nosql.specification.document import to_filter

        filter_dict = to_filter(spec)
        combined = self._base_filter()
        combined.update(filter_dict)
        entities: builtins.list[TEntity] = []
        async for doc in self._collection.find(combined):  # type: ignore[attr-defined]
            entities.append(await self._document_to_entity(doc))
        return entities

    async def count(self, **filters: Any) -> int:
        """Count documents matching filters.

        Args:
            **filters: Keyword filters applied as equality matches.

        Returns:
            Document count.
        """
        filter_dict = self._build_filter(**filters)
        return await self._collection.count_documents(filter_dict)

    # ── Write operations ─────────────────────────────────────────

    async def save(self, entity: TEntity) -> TEntity:
        """Insert or update a document (upsert semantics).

        Args:
            entity: The domain entity to persist.

        Returns:
            The persisted entity (possibly with generated ID).
        """
        doc = await self._entity_to_document(entity)
        doc_id = doc.get(self.id_field)
        if doc_id:
            await self._collection.update_one(
                {self.id_field: doc_id},
                {"$set": doc},
                upsert=True,
            )
        else:
            result = await self._collection.insert_one(doc)
            doc[self.id_field] = result.document_id
        return await self._document_to_entity(doc)

    async def delete(self, document_id: TKey) -> bool:
        """Delete a document by ID.

        Uses soft delete if configured, otherwise performs hard delete.

        Args:
            document_id: The document identifier.

        Returns:
            ``True`` if a document was deleted / marked.
        """
        if self._soft_delete:
            result = await self._collection.update_one(
                {self.id_field: document_id},
                {
                    "$set": {
                        "_deleted": True,
                        "_deleted_at": datetime.now(UTC),
                    }
                },
            )
            return result.modified_count > 0
        result = await self._collection.delete_one({self.id_field: document_id})
        return result.matched_count > 0

    async def save_many(
        self, entities: builtins.list[TEntity]
    ) -> builtins.list[TEntity]:
        """Bulk insert documents.

        Args:
            entities: List of domain entities.

        Returns:
            List of persisted entities.
        """
        docs = [await self._entity_to_document(e) for e in entities]
        await self._collection.insert_many(docs)
        return [await self._document_to_entity(d) for d in docs]

    async def delete_many(self, document_ids: builtins.list[TKey]) -> int:
        """Bulk delete documents by IDs.

        Args:
            document_ids: List of document identifiers.

        Returns:
            Number of documents deleted.
        """
        if self._soft_delete:
            result = await self._collection.update_many(
                {self.id_field: {"$in": document_ids}},
                {
                    "$set": {
                        "_deleted": True,
                        "_deleted_at": datetime.now(UTC),
                    }
                },
            )
            return result.modified_count
        result = await self._collection.delete_many(
            {self.id_field: {"$in": document_ids}},
        )
        return result.matched_count

    # ── Internal helpers ─────────────────────────────────────────

    def _base_filter(self) -> dict[str, Any]:
        """Build the base filter applied to all queries."""
        base: dict[str, Any] = {}
        if self._soft_delete:
            base["_deleted"] = {"$ne": True}
        return base

    def _build_filter(self, **kwargs: Any) -> dict[str, Any]:
        """Convert keyword filters to a MongoDB filter dict."""
        filter_dict = self._base_filter()
        filter_dict.update(kwargs)
        return filter_dict


__all__ = ["DocumentRepository"]
