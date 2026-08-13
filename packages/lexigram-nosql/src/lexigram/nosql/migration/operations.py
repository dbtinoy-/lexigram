"""Concrete migration operations for NoSQL schema management.

Provides reusable operations that can be registered with
``MigrationManager.add()`` to create indexes, add validation rules,
rename fields, and manage collection schemas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger
from lexigram.nosql.migration.manager import MigrationOperation

if TYPE_CHECKING:
    from lexigram.contracts.data.nosql.nosql import DocumentStoreProtocol

logger = get_logger(__name__)


class CreateIndex(MigrationOperation):
    """Create an index on a collection.

    Example::

        CreateIndex(
            collection="users",
            keys=[("email", 1)],
            unique=True,
            name="idx_users_email",
        )
    """

    def __init__(
        self,
        collection: str,
        keys: list[tuple[str, int]],
        *,
        unique: bool = False,
        name: str | None = None,
    ) -> None:
        """Initialize create index operation.

        Args:
            collection: Target collection name.
            keys: Index key specification (field, direction) pairs.
            unique: Whether the index enforces uniqueness.
            name: Optional custom index name.
        """
        self.collection = collection
        self.keys = keys
        self.unique = unique
        self.name = name

    async def execute(self, store: DocumentStoreProtocol) -> None:
        """Create the index on the specified collection."""
        col = store.collection(self.collection)
        index_name = await col.create_index(
            self.keys,
            unique=self.unique,
            name=self.name,
        )
        logger.info(
            "migration.index_created",
            collection=self.collection,
            index=index_name,
        )


class DropIndex(MigrationOperation):
    """Drop an index from a collection.

    Example::

        DropIndex(collection="users", name="idx_users_email")
    """

    def __init__(self, collection: str, name: str) -> None:
        """Initialize drop index operation.

        Args:
            collection: Target collection name.
            name: Index name to drop.
        """
        self.collection = collection
        self.name = name

    async def execute(self, store: DocumentStoreProtocol) -> None:
        """Drop the index from the specified collection."""
        col = store.collection(self.collection)
        # Access raw motor collection for drop_index
        if hasattr(col, "_col"):
            await col._col.drop_index(self.name)
            logger.info(
                "migration.index_dropped",
                collection=self.collection,
                index=self.name,
            )


class RenameField(MigrationOperation):
    """Rename a field across all documents in a collection.

    Example::

        RenameField(collection="users", old_name="username", new_name="name")
    """

    def __init__(self, collection: str, old_name: str, new_name: str) -> None:
        """Initialize rename field operation.

        Args:
            collection: Target collection name.
            old_name: Current field name.
            new_name: New field name.
        """
        self.collection = collection
        self.old_name = old_name
        self.new_name = new_name

    async def execute(self, store: DocumentStoreProtocol) -> None:
        """Rename the field in all documents."""
        col = store.collection(self.collection)
        await col.update_many(
            {self.old_name: {"$exists": True}},
            {"$rename": {self.old_name: self.new_name}},
        )
        logger.info(
            "migration.field_renamed",
            collection=self.collection,
            old_name=self.old_name,
            new_name=self.new_name,
        )


class AddField(MigrationOperation):
    """Add a field with a default value to all documents missing it.

    Example::

        AddField(collection="users", field="is_active", default_value=True)
    """

    def __init__(
        self,
        collection: str,
        field: str,
        default_value: Any,
    ) -> None:
        """Initialize add field operation.

        Args:
            collection: Target collection name.
            field: Field name to add.
            default_value: Default value to set for the new field.
        """
        self.collection = collection
        self.field = field
        self.default_value = default_value

    async def execute(self, store: DocumentStoreProtocol) -> None:
        """Add the field to documents that don't have it."""
        col = store.collection(self.collection)
        await col.update_many(
            {self.field: {"$exists": False}},
            {"$set": {self.field: self.default_value}},
        )
        logger.info(
            "migration.field_added",
            collection=self.collection,
            field=self.field,
        )


class DropCollection(MigrationOperation):
    """Drop an entire collection.

    Example::

        DropCollection(collection="legacy_events")
    """

    def __init__(self, collection: str) -> None:
        """Initialize drop collection operation.

        Args:
            collection: Collection name to drop.
        """
        self.collection = collection

    async def execute(self, store: DocumentStoreProtocol) -> None:
        """Drop the collection from the store."""
        await store.drop_collection(self.collection)
        logger.info(
            "migration.collection_dropped",
            collection=self.collection,
        )


__all__ = [
    "AddField",
    "CreateIndex",
    "DropCollection",
    "DropIndex",
    "RenameField",
]
