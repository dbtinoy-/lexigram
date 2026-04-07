"""DynamoDB collection: CollectionProtocol implementation for DynamoDB tables."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import uuid

from lexigram.contracts.data.nosql.nosql import BulkWriteResult, DocumentResult
from lexigram.logging import get_logger
from lexigram.nosql.exceptions import DuplicateKeyError, NoSQLError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = get_logger(__name__)

# Sentinel for "no value" (avoids confusing None with a missing key).
_MISSING = object()

# DynamoDB expression attribute name prefix.
_ATTR_PREFIX = "#attr_"
_VAL_PREFIX = ":val_"


def _build_filter_expression(
    filter_doc: dict[str, Any],
) -> tuple[str, dict[str, str], dict[str, Any]]:
    """Convert a flat equality filter dict into DynamoDB FilterExpression parts.

    Args:
        filter_doc: Mapping of field_name → expected_value.

    Returns:
        A tuple of (filter_expression_str, expression_attribute_names,
        expression_attribute_values).
    """
    parts: list[str] = []
    names: dict[str, str] = {}
    values: dict[str, Any] = {}
    for i, (key, val) in enumerate(filter_doc.items()):
        name_ph = f"{_ATTR_PREFIX}{i}"
        val_ph = f"{_VAL_PREFIX}{i}"
        names[name_ph] = key
        values[val_ph] = val
        parts.append(f"{name_ph} = {val_ph}")
    return " AND ".join(parts), names, values


def _build_update_expression(
    update_doc: dict[str, Any],
) -> tuple[str, dict[str, str], dict[str, Any]]:
    """Convert an update dict into DynamoDB UpdateExpression parts.

    Args:
        update_doc: Mapping of field_name → new_value.

    Returns:
        A tuple of (update_expression_str, expression_attribute_names,
        expression_attribute_values).
    """
    set_parts: list[str] = []
    names: dict[str, str] = {}
    values: dict[str, Any] = {}
    for i, (key, val) in enumerate(update_doc.items()):
        name_ph = f"{_ATTR_PREFIX}{i}"
        val_ph = f"{_VAL_PREFIX}{i}"
        names[name_ph] = key
        values[val_ph] = val
        set_parts.append(f"{name_ph} = {val_ph}")
    return "SET " + ", ".join(set_parts), names, values


class DynamoDBCollection:
    """A DynamoDB table that implements ``CollectionProtocol``.

    Wraps an aioboto3 DynamoDB ``Table`` resource and translates
    operations into framework-level ``DocumentResult`` / ``BulkWriteResult``
    types.

    DynamoDB does not support server-side arbitrary filter scans with the
    same richness as MongoDB.  This implementation uses ``scan`` with a
    ``FilterExpression`` for unsorted queries.  For production workloads
    requiring high-performance reads, callers should define DynamoDB GSIs
    and query against them directly.

    The ``_id`` field maps to the DynamoDB partition key (``PK``).  When
    inserting a document without ``_id``, a UUID4 is generated.

    Args:
        table: aioboto3 / boto3 DynamoDB ``Table`` resource (type-erased).
        name: Logical table / collection name (used in log messages).
        pk_field: DynamoDB partition key attribute name. Defaults to ``_id``.
    """

    def __init__(
        self,
        table: Any,
        name: str,
        *,
        pk_field: str = "_id",
    ) -> None:
        self._table = table
        self._name = name
        self._pk_field = pk_field

    @property
    def name(self) -> str:
        """Table / collection name."""
        return self._name

    # ──────────────────────────────────────────────────────────────
    # Insert
    # ──────────────────────────────────────────────────────────────

    async def insert_one(self, document: dict[str, Any]) -> DocumentResult:
        """Insert a single document into the DynamoDB table.

        If the document lacks a ``_id`` field (or the configured pk_field),
        a UUID4 is generated and injected before writing.

        Args:
            document: Document to insert.

        Returns:
            :class:`~lexigram.contracts.data.nosql.nosql.DocumentResult`
            with ``document_id`` set to the generated or provided ``_id``.

        Raises:
            :class:`~lexigram.nosql.exceptions.DuplicateKeyError`: When
                DynamoDB raises ``ConditionalCheckFailedException`` because
                an item with the same primary key already exists.
            :class:`~lexigram.nosql.exceptions.NoSQLError`: On other
                DynamoDB / aioboto3 failures.
        """
        doc = dict(document)
        if self._pk_field not in doc or doc[self._pk_field] is None:
            doc[self._pk_field] = str(uuid.uuid4())

        document_id: str = str(doc[self._pk_field])
        try:
            await self._table.put_item(
                Item=doc,
                ConditionExpression=f"attribute_not_exists({self._pk_field})",
            )
            logger.debug(
                "nosql.dynamodb.insert_one",
                table=self._name,
                document_id=document_id,
            )
            return DocumentResult(document_id=document_id, acknowledged=True)
        except (
            self._table.meta.client.exceptions.ConditionalCheckFailedException
        ) as exc:
            raise DuplicateKeyError(
                f"Item with {self._pk_field}={document_id!r} already exists "
                f"in table {self._name!r}"
            ) from exc
        except Exception as exc:  # noqa: BLE001  # DynamoDB SDK raises varied exception types
            raise NoSQLError(
                f"insert_one failed on DynamoDB table {self._name!r}: {exc}"
            ) from exc

    async def insert_many(self, documents: list[dict[str, Any]]) -> BulkWriteResult:
        """Insert multiple documents via a DynamoDB batch_writer.

        Uses ``batch_writer()`` which automatically handles request
        batching in groups of 25 (DynamoDB limit) and retries on
        unprocessed items.

        Args:
            documents: Documents to insert.

        Returns:
            :class:`~lexigram.contracts.data.nosql.nosql.BulkWriteResult`.

        Raises:
            :class:`~lexigram.nosql.exceptions.NoSQLError`: On DynamoDB failure.
        """
        if not documents:
            return BulkWriteResult()

        inserted_ids: list[str] = []
        prepared: list[dict[str, Any]] = []
        for doc in documents:
            item = dict(doc)
            if self._pk_field not in item or item[self._pk_field] is None:
                item[self._pk_field] = str(uuid.uuid4())
            inserted_ids.append(str(item[self._pk_field]))
            prepared.append(item)

        try:
            async with self._table.batch_writer() as batch:
                for item in prepared:
                    await batch.put_item(Item=item)
        except Exception as exc:  # noqa: BLE001
            raise NoSQLError(
                f"insert_many failed on DynamoDB table {self._name!r}: {exc}"
            ) from exc

        return BulkWriteResult(
            inserted_count=len(inserted_ids),
            upserted_ids=inserted_ids,
        )

    # ──────────────────────────────────────────────────────────────
    # Find
    # ──────────────────────────────────────────────────────────────

    async def find_one(
        self,
        filter: dict[str, Any],  # noqa: A002
        *,
        projection: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Find the first document matching *filter*.

        When *filter* contains only the primary key field, a
        ``get_item`` (O(1)) is used instead of a scan.  For all other
        filters a ``scan`` with a ``FilterExpression`` is issued.

        Args:
            filter: Field equality conditions.
            projection: Ignored (DynamoDB projection expressions require
                knowing attribute names ahead of time; not enforced here).

        Returns:
            First matching document dict, or ``None``.
        """
        # Fast path: primary key only lookup.
        if list(filter.keys()) == [self._pk_field]:
            return await self._get_by_pk(filter[self._pk_field])

        docs = [doc async for doc in await self.find(filter)]
        return docs[0] if docs else None

    async def find(
        self,
        filter: dict[str, Any],  # noqa: A002
        *,
        projection: dict[str, Any] | None = None,
        sort: list[tuple[str, int]] | None = None,
        skip: int = 0,
        limit: int = 0,
    ) -> AsyncIterator[dict[str, Any]]:
        """Scan the table and yield documents matching *filter*.

        All filter predicates are equality checks combined with AND.
        For large tables, consider adding GSIs and using ``query`` for
        performance-sensitive paths.

        Args:
            filter: Field equality conditions.
            projection: Ignored.
            sort: In-memory sort applied after the scan.
            skip: Number of leading results to skip.
            limit: Maximum number of results to return (``0`` = unlimited).

        Yields:
            Matching document dicts.
        """
        return self._scan_iter(
            filter,
            sort=sort,
            skip=skip,
            limit=limit,
        )

    async def _scan_iter(
        self,
        filter: dict[str, Any],  # noqa: A002
        *,
        sort: list[tuple[str, int]] | None = None,
        skip: int = 0,
        limit: int = 0,
    ) -> AsyncIterator[dict[str, Any]]:
        """Internal scan that yields matching documents."""
        try:
            scan_kwargs: dict[str, Any] = {}
            if filter:
                expr, names, values = _build_filter_expression(filter)
                scan_kwargs["FilterExpression"] = expr
                scan_kwargs["ExpressionAttributeNames"] = names
                scan_kwargs["ExpressionAttributeValues"] = values

            items: list[dict[str, Any]] = []
            # Paginate through all results.
            response = await self._table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))
            while "LastEvaluatedKey" in response:
                scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = await self._table.scan(**scan_kwargs)
                items.extend(response.get("Items", []))

            # In-memory sort.
            if sort:
                for field_name, direction in reversed(sort):
                    items.sort(
                        key=lambda d: d.get(field_name) or "",
                        reverse=(direction < 0),
                    )

            if skip:
                items = items[skip:]
            if limit:
                items = items[:limit]

            for item in items:
                yield item

        except Exception as exc:  # noqa: BLE001
            raise NoSQLError(
                f"find failed on DynamoDB table {self._name!r}: {exc}"
            ) from exc

    async def _get_by_pk(self, pk_value: Any) -> dict[str, Any] | None:
        """Retrieve a single item by primary key using ``get_item``."""
        try:
            response = await self._table.get_item(Key={self._pk_field: pk_value})
            return response.get("Item")
        except Exception as exc:  # noqa: BLE001
            raise NoSQLError(
                f"find_one (get_item) failed on DynamoDB table {self._name!r}: {exc}"
            ) from exc

    # ──────────────────────────────────────────────────────────────
    # Update
    # ──────────────────────────────────────────────────────────────

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
            update: Fields to set on the matching item.
            upsert: If ``True`` and no document matches, insert *update*.

        Returns:
            :class:`~lexigram.contracts.data.nosql.nosql.DocumentResult`.
        """
        doc = await self.find_one(filter)
        if doc is None:
            if upsert:
                result = await self.insert_one(update)
                return DocumentResult(
                    document_id=result.document_id,
                    upserted_id=result.document_id,
                    acknowledged=True,
                )
            return DocumentResult(matched_count=0, acknowledged=True)

        pk_value = doc[self._pk_field]
        return await self._update_by_pk(pk_value, update)

    async def update_many(
        self,
        filter: dict[str, Any],  # noqa: A002
        update: dict[str, Any],
    ) -> DocumentResult:
        """Update all documents matching *filter*.

        Args:
            filter: Field equality conditions.
            update: Fields to set on each matched item.

        Returns:
            :class:`~lexigram.contracts.data.nosql.nosql.DocumentResult`.
        """
        docs = [doc async for doc in await self.find(filter)]
        modified = 0
        for doc in docs:
            await self._update_by_pk(doc[self._pk_field], update)
            modified += 1
        return DocumentResult(
            matched_count=len(docs),
            modified_count=modified,
            acknowledged=True,
        )

    async def _update_by_pk(
        self,
        pk_value: Any,
        update: dict[str, Any],
    ) -> DocumentResult:
        """Apply *update* fields to the item identified by *pk_value*."""
        update_expr, names, values = _build_update_expression(update)
        try:
            await self._table.update_item(
                Key={self._pk_field: pk_value},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=values,
            )
            return DocumentResult(
                document_id=str(pk_value),
                matched_count=1,
                modified_count=1,
                acknowledged=True,
            )
        except Exception as exc:  # noqa: BLE001
            raise NoSQLError(
                f"update_item failed on DynamoDB table {self._name!r}: {exc}"
            ) from exc

    # ──────────────────────────────────────────────────────────────
    # Delete
    # ──────────────────────────────────────────────────────────────

    async def delete_one(self, filter: dict[str, Any]) -> DocumentResult:  # noqa: A002
        """Delete the first document matching *filter*.

        Args:
            filter: Field equality conditions.

        Returns:
            :class:`~lexigram.contracts.data.nosql.nosql.DocumentResult`.
        """
        doc = await self.find_one(filter)
        if doc is None:
            return DocumentResult(matched_count=0, acknowledged=True)
        return await self._delete_by_pk(doc[self._pk_field])

    async def delete_many(self, filter: dict[str, Any]) -> DocumentResult:  # noqa: A002
        """Delete all documents matching *filter*.

        Args:
            filter: Field equality conditions.

        Returns:
            :class:`~lexigram.contracts.data.nosql.nosql.DocumentResult`.
        """
        docs = [doc async for doc in await self.find(filter)]
        for doc in docs:
            await self._delete_by_pk(doc[self._pk_field])
        return DocumentResult(
            matched_count=len(docs),
            acknowledged=True,
        )

    async def _delete_by_pk(self, pk_value: Any) -> DocumentResult:
        """Delete the item identified by *pk_value* from the table."""
        try:
            await self._table.delete_item(Key={self._pk_field: pk_value})
            return DocumentResult(
                document_id=str(pk_value),
                matched_count=1,
                acknowledged=True,
            )
        except Exception as exc:  # noqa: BLE001
            raise NoSQLError(
                f"delete_item failed on DynamoDB table {self._name!r}: {exc}"
            ) from exc

    # ──────────────────────────────────────────────────────────────
    # Count
    # ──────────────────────────────────────────────────────────────

    async def count_documents(self, filter: dict[str, Any] | None = None) -> int:  # noqa: A002
        """Count documents matching *filter* (full-table scan).

        Args:
            filter: Field equality conditions; ``None`` counts all items.

        Returns:
            Number of matching items.
        """
        count = 0
        async for _ in await self.find(filter or {}):
            count += 1
        return count


__all__ = ["DynamoDBCollection"]
