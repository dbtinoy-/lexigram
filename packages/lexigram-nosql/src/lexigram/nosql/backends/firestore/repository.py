"""Google Cloud Firestore repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.data.nosql.nosql import BulkWriteResult, DocumentResult
from lexigram.logging import get_logger
from lexigram.nosql.exceptions import (
    DocumentNotFoundError,
    DuplicateKeyError,
    NoSQLError,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = get_logger(__name__)


class FirestoreRepository:
    """A Firestore collection that implements ``CollectionProtocol``.

    Wraps a ``google.cloud.firestore_v1.AsyncCollectionReference`` and
    translates results into framework-level ``DocumentResult`` /
    ``BulkWriteResult`` types.

    This class exposes both the standard ``CollectionProtocol`` interface
    (``insert_one``, ``find_one``, ``find``, ``update_one``, ``delete_one``,
    etc.) and a simplified repository interface (``insert``, ``find_by_id``,
    ``find``, ``update``, ``delete``) as described in the backend specification.

    Args:
        col_ref: Firestore async collection reference (type-erased to avoid
            a hard import at module level).
        name: Collection path used in log messages.
    """

    def __init__(self, col_ref: Any, name: str) -> None:
        self._col = col_ref
        self._name = name

    @property
    def name(self) -> str:
        """Collection path / name."""
        return self._name

    # ==================================================================
    # Simplified repository interface (per specification)
    # ==================================================================

    async def insert(self, document: dict[str, Any]) -> DocumentResult:
        """Insert a document with an auto-generated Firestore document ID.

        Args:
            document: Document fields to store.

        Returns:
            :class:`~lexigram.contracts.data.nosql.nosql.DocumentResult`
            with ``document_id`` set to the new Firestore ID.

        Raises:
            :class:`~lexigram.nosql.exceptions.NoSQLError`: On Firestore failure.
        """
        try:
            _timestamp, doc_ref = await self._col.add(document)
            logger.debug(
                "nosql.firestore.insert",
                collection=self._name,
                document_id=doc_ref.id,
            )
            return DocumentResult(document_id=doc_ref.id, acknowledged=True)
        except Exception as exc:  # noqa: BLE001  # Firestore SDK raises varied exception types
            raise NoSQLError(
                f"insert failed on Firestore collection {self._name!r}: {exc}"
            ) from exc

    async def find_by_id(self, doc_id: str) -> dict[str, Any] | None:
        """Retrieve a document by its Firestore document ID.

        Args:
            doc_id: Firestore document ID.

        Returns:
            Document dict including a ``_id`` field, or ``None`` if not found.

        Raises:
            :class:`~lexigram.nosql.exceptions.NoSQLError`: On Firestore failure.
        """
        try:
            snapshot = await self._col.document(doc_id).get()
            if not snapshot.exists:
                return None
            data = snapshot.to_dict() or {}
            data["_id"] = snapshot.id
            return data
        except Exception as exc:  # noqa: BLE001  # SDK raises on invalid IDs / network errors
            raise NoSQLError(
                f"find_by_id failed on Firestore collection {self._name!r}: {exc}"
            ) from exc

    async def find_by_filter(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        """Query documents by field equality filters.

        Each key-value pair in *query* is applied as a ``where`` clause
        using the ``==`` operator.  Multiple conditions are AND-combined.

        Args:
            query: Mapping of ``field_name`` → ``expected_value``.

        Returns:
            List of matching document dicts, each augmented with ``_id``.

        Raises:
            :class:`~lexigram.nosql.exceptions.NoSQLError`: On Firestore failure.
        """
        try:
            q: Any = self._col
            for field, value in query.items():
                q = q.where(field, "==", value)

            results: list[dict[str, Any]] = []
            async for snapshot in q.stream():
                data = snapshot.to_dict() or {}
                data["_id"] = snapshot.id
                results.append(data)
            return results
        except Exception as exc:  # noqa: BLE001  # SDK raises on invalid query operators
            raise NoSQLError(
                f"find failed on Firestore collection {self._name!r}: {exc}"
            ) from exc

    async def update(self, doc_id: str, data: dict[str, Any]) -> DocumentResult:
        """Update specific fields of an existing document (merge semantics).

        Only the keys present in *data* are modified; all other fields are
        preserved.

        Args:
            doc_id: Firestore document ID.
            data: Fields to update.

        Returns:
            :class:`~lexigram.contracts.data.nosql.nosql.DocumentResult`.

        Raises:
            :class:`~lexigram.nosql.exceptions.DocumentNotFoundError`: If
                the document does not exist.
            :class:`~lexigram.nosql.exceptions.NoSQLError`: On Firestore failure.
        """
        try:
            doc_ref = self._col.document(doc_id)
            # Verify existence before updating to provide a clear error.
            snapshot = await doc_ref.get()
            if not snapshot.exists:
                raise DocumentNotFoundError(
                    f"Document {doc_id!r} not found in {self._name!r}"
                )
            await doc_ref.update(data)
            return DocumentResult(
                document_id=doc_id,
                modified_count=1,
                acknowledged=True,
            )
        except DocumentNotFoundError:
            raise
        except Exception as exc:  # noqa: BLE001  # SDK raises varied exceptions on update failure
            raise NoSQLError(
                f"update failed on Firestore collection {self._name!r}: {exc}"
            ) from exc

    async def delete(self, doc_id: str) -> DocumentResult:
        """Delete a document by Firestore document ID.

        Firestore ``delete()`` is idempotent — deleting a non-existent
        document is a no-op rather than an error.

        Args:
            doc_id: Firestore document ID.

        Returns:
            :class:`~lexigram.contracts.data.nosql.nosql.DocumentResult`.

        Raises:
            :class:`~lexigram.nosql.exceptions.NoSQLError`: On Firestore failure.
        """
        try:
            await self._col.document(doc_id).delete()
            return DocumentResult(
                document_id=doc_id,
                matched_count=1,
                acknowledged=True,
            )
        except Exception as exc:  # noqa: BLE001  # SDK raises on network / permission errors
            raise NoSQLError(
                f"delete failed on Firestore collection {self._name!r}: {exc}"
            ) from exc

    # ==================================================================
    # CollectionProtocol interface (compatible with AbstractDocumentStore)
    # ==================================================================

    async def insert_one(self, document: dict[str, Any]) -> DocumentResult:
        """Insert a single document (``CollectionProtocol`` alias for :meth:`insert`).

        Args:
            document: Document fields to store.

        Returns:
            :class:`~lexigram.contracts.data.nosql.nosql.DocumentResult`.
        """
        return await self.insert(document)

    async def insert_many(self, documents: list[dict[str, Any]]) -> BulkWriteResult:
        """Insert multiple documents in a sequential batch.

        Args:
            documents: Documents to insert.

        Returns:
            :class:`~lexigram.contracts.data.nosql.nosql.BulkWriteResult`.

        Raises:
            :class:`~lexigram.nosql.exceptions.DuplicateKeyError`: If a
                document-level constraint is violated (not applicable for
                auto-ID inserts).
            :class:`~lexigram.nosql.exceptions.NoSQLError`: On Firestore failure.
        """
        inserted_ids: list[str] = []
        try:
            # Use a write batch for atomic multi-document inserts.
            batch = self._col._client.batch()  # noqa: SLF001  # access batch via parent client
            doc_refs = []
            for doc in documents:
                ref = self._col.document()
                doc_refs.append(ref)
                batch.set(ref, doc)
            await batch.commit()
            inserted_ids = [ref.id for ref in doc_refs]
        except Exception as exc:  # noqa: BLE001  # SDK raises varied exceptions on batch failure
            if "already exists" in str(exc).lower():
                raise DuplicateKeyError(
                    f"Duplicate key in Firestore collection {self._name!r}: {exc}"
                ) from exc
            raise NoSQLError(f"insert_many failed on {self._name!r}: {exc}") from exc

        return BulkWriteResult(
            inserted_count=len(inserted_ids),
            upserted_ids=inserted_ids,
        )

    async def find_one(
        self,
        filter: dict[str, Any],  # noqa: A002
        *,
        projection: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Find the first document matching *filter*.

        Args:
            filter: Field equality conditions.
            projection: Ignored (Firestore does not support field projections
                in the same way as MongoDB; all fields are always returned).

        Returns:
            First matching document dict with ``_id`` field, or ``None``.
        """
        results = await self.find_by_filter(filter)
        return results[0] if results else None

    async def find(
        self,
        filter: dict[str, Any],  # noqa: A002
        *,
        projection: dict[str, Any] | None = None,
        sort: list[tuple[str, int]] | None = None,
        skip: int = 0,
        limit: int = 0,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield documents matching *filter*.

        Args:
            filter: Field equality conditions.
            projection: Ignored (Firestore always returns all fields).
            sort: List of ``(field, direction)`` tuples.  Direction ``1`` →
                ascending; ``-1`` → descending.
            skip: Number of leading results to skip.
            limit: Maximum number of results to return (``0`` = unlimited).

        Yields:
            Matching document dicts augmented with ``_id``.
        """
        try:
            q: Any = self._col
            for field, value in filter.items():
                q = q.where(field, "==", value)

            if sort:
                from google.cloud.firestore_v1 import (
                    Query,
                )

                for field_name, direction in sort:
                    order = Query.ASCENDING if direction >= 0 else Query.DESCENDING
                    q = q.order_by(field_name, direction=order)

            if skip:
                q = q.offset(skip)
            if limit:
                q = q.limit(limit)

            async for snapshot in q.stream():
                data = snapshot.to_dict() or {}
                data["_id"] = snapshot.id
                yield data
        except Exception as exc:  # noqa: BLE001  # SDK raises on invalid query operators
            raise NoSQLError(
                f"find failed on Firestore collection {self._name!r}: {exc}"
            ) from exc

    async def update_one(
        self,
        filter: dict[str, Any],  # noqa: A002
        update: dict[str, Any],
        *,
        upsert: bool = False,
    ) -> DocumentResult:
        """Update the first document matching *filter*.

        Args:
            filter: Field equality conditions used to locate the document.
            update: Fields to update (merged, not replaced).
            upsert: If ``True`` and no document matches, insert *update* as a
                new document.

        Returns:
            :class:`~lexigram.contracts.data.nosql.nosql.DocumentResult`.
        """
        docs = [d async for d in self.find(filter)]
        if not docs:
            if upsert:
                result = await self.insert(update)
                return DocumentResult(
                    document_id=result.document_id,
                    upserted_id=result.document_id,
                    acknowledged=True,
                )
            return DocumentResult(matched_count=0, acknowledged=True)

        doc_id: str = docs[0]["_id"]
        return await self.update(doc_id, update)

    async def update_many(
        self,
        filter: dict[str, Any],  # noqa: A002
        update: dict[str, Any],
    ) -> DocumentResult:
        """Update all documents matching *filter*.

        Args:
            filter: Field equality conditions.
            update: Fields to update on each matched document.

        Returns:
            :class:`~lexigram.contracts.data.nosql.nosql.DocumentResult`
            with ``modified_count`` set to the number of updated documents.
        """
        docs: list[dict[str, Any]] = []
        async for doc in self.find(filter):
            docs.append(doc)

        modified = 0
        for doc in docs:
            await self.update(doc["_id"], update)
            modified += 1
        return DocumentResult(
            matched_count=len(docs),
            modified_count=modified,
            acknowledged=True,
        )

    async def delete_one(self, filter: dict[str, Any]) -> DocumentResult:  # noqa: A002
        """Delete the first document matching *filter*.

        Args:
            filter: Field equality conditions.

        Returns:
            :class:`~lexigram.contracts.data.nosql.nosql.DocumentResult`.
        """
        docs = [d async for d in self.find(filter)]
        if not docs:
            return DocumentResult(matched_count=0, acknowledged=True)
        return await self.delete(docs[0]["_id"])

    async def delete_many(self, filter: dict[str, Any]) -> DocumentResult:  # noqa: A002
        """Delete all documents matching *filter*.

        Args:
            filter: Field equality conditions.

        Returns:
            :class:`~lexigram.contracts.data.nosql.nosql.DocumentResult`
            with ``matched_count`` set to the number of deleted documents.
        """
        docs: list[dict[str, Any]] = []
        async for doc in self.find(filter):
            docs.append(doc)

        for doc in docs:
            await self.delete(doc["_id"])
        return DocumentResult(
            matched_count=len(docs),
            acknowledged=True,
        )

    async def count_documents(self, filter: dict[str, Any] | None = None) -> int:  # noqa: A002
        """Count documents matching *filter*.

        Args:
            filter: Field equality conditions; ``None`` counts all documents.

        Returns:
            Number of matching documents.
        """
        q: Any = self._col
        if filter:
            for field, value in filter.items():
                q = q.where(field, "==", value)
        try:
            results = await q.count().get()
            # Firestore COUNT returns a list of AggregationResult rows.
            return results[0][0].value if results else 0
        except Exception as exc:  # noqa: BLE001  # COUNT may not be available in all SDK versions
            logger.debug(
                "nosql.firestore.count_fallback",
                collection=self._name,
                error=str(exc),
            )
            # Fallback: stream and count manually.
            count = 0
            async for _ in q.stream():
                count += 1
            return count

    async def replace_one(
        self,
        filter: dict[str, Any],  # noqa: A002
        replacement: dict[str, Any],
        *,
        upsert: bool = False,
    ) -> DocumentResult:
        """Replace the first document matching *filter* (full replacement).

        Args:
            filter: Field equality conditions.
            replacement: New document contents (completely replaces the old doc).
            upsert: Insert if no document is found.

        Returns:
            :class:`~lexigram.contracts.data.nosql.nosql.DocumentResult`.
        """
        docs = [d async for d in self.find(filter)]
        if not docs:
            if upsert:
                result = await self.insert(replacement)
                return DocumentResult(upserted_id=result.document_id, acknowledged=True)
            return DocumentResult(matched_count=0, acknowledged=True)

        doc_id: str = docs[0]["_id"]
        await self._col.document(doc_id).set(replacement)
        return DocumentResult(
            document_id=doc_id,
            matched_count=1,
            modified_count=1,
            acknowledged=True,
        )


__all__ = ["FirestoreRepository"]
