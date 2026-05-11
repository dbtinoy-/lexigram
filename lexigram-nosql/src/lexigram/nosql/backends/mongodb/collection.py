"""MongoDB collection implementation of CollectionProtocol."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

pymongo: Any
try:
    import pymongo as _pymongo

    pymongo = _pymongo
except ImportError:
    pymongo = None

from lexigram.contracts.data.nosql.nosql import BulkWriteResult, DocumentResult
from lexigram.logging import get_logger
from lexigram.nosql.exceptions import DuplicateKeyError, NoSQLError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = get_logger(__name__)


class MongoDBCollection:
    """A MongoDB collection that implements ``CollectionProtocol``.

    Wraps a motor ``AsyncIOMotorCollection`` and translates results
    into framework-level ``DocumentResult`` / ``BulkWriteResult`` types.
    """

    def __init__(self, motor_collection: Any) -> None:
        self._col = motor_collection
        self._name: str = motor_collection.name

    @property
    def name(self) -> str:
        """Collection name."""
        return self._name

    # ── Insert ───────────────────────────────────────────────────

    async def insert_one(self, document: dict[str, Any]) -> DocumentResult:
        """Insert a single document."""
        try:
            result = await self._col.insert_one(document)
            return DocumentResult(
                document_id=str(result.inserted_id),
                acknowledged=result.acknowledged,
            )
        except pymongo.errors.PyMongoError as exc:
            if "duplicate key" in str(exc).lower() or "E11000" in str(exc):
                raise DuplicateKeyError(
                    f"Duplicate key in {self._name}: {exc}"
                ) from exc
            raise NoSQLError(f"insert_one failed on {self._name}: {exc}") from exc

    async def insert_many(self, documents: list[dict[str, Any]]) -> BulkWriteResult:
        """Insert multiple documents."""
        try:
            result = await self._col.insert_many(documents)
            return BulkWriteResult(
                inserted_count=len(result.inserted_ids),
                upserted_ids=[str(oid) for oid in result.inserted_ids],
            )
        except pymongo.errors.PyMongoError as exc:
            if "duplicate key" in str(exc).lower() or "E11000" in str(exc):
                raise DuplicateKeyError(
                    f"Duplicate key in {self._name}: {exc}"
                ) from exc
            raise NoSQLError(f"insert_many failed on {self._name}: {exc}") from exc

    # ── Find ─────────────────────────────────────────────────────

    async def find_one(
        self,
        filter: dict[str, Any],
        *,
        projection: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Find a single document matching the filter."""
        doc: dict[str, Any] | None = await self._col.find_one(
            filter, projection=projection
        )
        return doc

    async def find(
        self,
        filter: dict[str, Any],
        *,
        projection: dict[str, Any] | None = None,
        sort: list[tuple[str, int]] | None = None,
        skip: int = 0,
        limit: int = 0,
    ) -> AsyncIterator[dict[str, Any]]:
        """Find documents matching the filter. Returns async iterator."""
        cursor = self._col.find(filter, projection=projection)
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        async for doc in cursor:
            yield doc

    # ── Update ───────────────────────────────────────────────────

    async def update_one(
        self,
        filter: dict[str, Any],
        update: dict[str, Any],
        *,
        upsert: bool = False,
    ) -> DocumentResult:
        """Update a single document matching the filter."""
        result = await self._col.update_one(filter, update, upsert=upsert)
        return DocumentResult(
            matched_count=result.matched_count,
            modified_count=result.modified_count,
            upserted_id=str(result.upserted_id) if result.upserted_id else None,
            acknowledged=result.acknowledged,
        )

    async def update_many(
        self,
        filter: dict[str, Any],
        update: dict[str, Any],
    ) -> DocumentResult:
        """Update all documents matching the filter."""
        result = await self._col.update_many(filter, update)
        return DocumentResult(
            matched_count=result.matched_count,
            modified_count=result.modified_count,
            acknowledged=result.acknowledged,
        )

    # ── Delete ───────────────────────────────────────────────────

    async def delete_one(self, filter: dict[str, Any]) -> DocumentResult:
        """Delete a single document matching the filter."""
        result = await self._col.delete_one(filter)
        return DocumentResult(
            matched_count=result.deleted_count,
            acknowledged=result.acknowledged,
        )

    async def delete_many(self, filter: dict[str, Any]) -> DocumentResult:
        """Delete all documents matching the filter."""
        result = await self._col.delete_many(filter)
        return DocumentResult(
            matched_count=result.deleted_count,
            acknowledged=result.acknowledged,
        )

    # ── Replace / Find-and-Modify ────────────────────────────────

    async def replace_one(
        self,
        filter: dict[str, Any],
        replacement: dict[str, Any],
        *,
        upsert: bool = False,
    ) -> DocumentResult:
        """Replace a single document matching the filter."""
        result = await self._col.replace_one(filter, replacement, upsert=upsert)
        return DocumentResult(
            matched_count=result.matched_count,
            modified_count=result.modified_count,
            upserted_id=str(result.upserted_id) if result.upserted_id else None,
            acknowledged=result.acknowledged,
        )

    async def find_one_and_update(
        self,
        filter: dict[str, Any],
        update: dict[str, Any],
        *,
        upsert: bool = False,
        return_document: bool = True,
    ) -> dict[str, Any] | None:
        """Atomically find and update a document."""
        from pymongo import ReturnDocument

        return_doc = ReturnDocument.AFTER if return_document else ReturnDocument.BEFORE
        updated: dict[str, Any] | None = await self._col.find_one_and_update(
            filter,
            update,
            upsert=upsert,
            return_document=return_doc,
        )
        return updated

    # ── Count / Index ────────────────────────────────────────────

    async def count_documents(self, filter: dict[str, Any] | None = None) -> int:
        """Count documents matching the filter."""
        count: int = await self._col.count_documents(filter or {})
        return count

    async def create_index(
        self,
        keys: list[tuple[str, int]],
        *,
        unique: bool = False,
        name: str | None = None,
    ) -> str:
        """Create an index on the collection. Returns the index name."""
        kwargs: dict[str, Any] = {"unique": unique}
        if name:
            kwargs["name"] = name
        index_name: str = await self._col.create_index(keys, **kwargs)
        return index_name

    # ── Aggregation ──────────────────────────────────────────────

    async def aggregate(
        self,
        pipeline: list[dict[str, Any]],
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute an aggregation pipeline."""
        cursor = self._col.aggregate(pipeline)
        async for doc in cursor:
            yield doc

    async def list_indexes(self) -> list[dict[str, Any]]:
        """List all indexes on the collection."""
        cursor = self._col.list_indexes()
        return [doc async for doc in cursor]

    async def distinct(
        self,
        key: str,
        filter: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Get distinct values for a specified key."""
        values: list[Any] = await self._col.distinct(key, filter=filter or {})
        return values

    async def bulk_write(self, operations: list[Any]) -> BulkWriteResult:
        """Execute multiple write operations in a single batch."""
        if not operations:
            return BulkWriteResult()

        try:
            result = await self._col.bulk_write(operations)
            return BulkWriteResult(
                inserted_count=result.inserted_count,
                matched_count=result.matched_count,
                modified_count=result.modified_count,
                deleted_count=result.deleted_count,
                upserted_ids=[str(oid) for oid in result.upserted_ids.values()]
                if result.upserted_ids
                else [],
            )
        except pymongo.errors.PyMongoError as exc:
            raise NoSQLError(f"bulk_write failed on {self._name}: {exc}") from exc


__all__ = ["MongoDBCollection"]
