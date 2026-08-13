"""Schema migration manager for NoSQL collections.

Provides ordered, idempotent schema migrations for document stores —
creating indexes, adding validation rules, and renaming fields.
Each migration is identified by a version string and only applied once.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.data.nosql.nosql import (
        CollectionProtocol,
        DocumentStoreProtocol,
    )

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class MigrationRecord:
    """Metadata about an applied migration."""

    version: str
    description: str
    applied_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class MigrationManager:
    """Manage schema migrations for a document store.

    Tracks applied migrations in a ``_migrations`` collection and
    executes pending ones in version order.

    Example::

        manager = MigrationManager(store)
        manager.add("001", "Create users index", CreateIndex(
            collection="users",
            keys=[("email", 1)],
            unique=True,
        ))
        manager.add("002", "Create events compound index", CreateIndex(
            collection="events",
            keys=[("stream_id", 1), ("stream_version", 1)],
            unique=True,
        ))
        await manager.migrate()
    """

    MIGRATIONS_COLLECTION = "_migrations"

    def __init__(
        self,
        store: DocumentStoreProtocol,
        *,
        migrations_collection: str = MIGRATIONS_COLLECTION,
    ) -> None:
        """Initialize migration manager.

        Args:
            store: The document store to manage.
            migrations_collection: Name of the collection tracking applied migrations.
        """
        self._store = store
        self._migrations_col_name = migrations_collection
        self._pending: list[tuple[str, str, MigrationOperation]] = []

    @property
    def _migrations_col(self) -> CollectionProtocol:
        """Collection that tracks applied migrations."""
        return self._store.collection(self._migrations_col_name)

    def add(
        self,
        version: str,
        description: str,
        operation: MigrationOperation,
    ) -> MigrationManager:
        """Register a migration to be applied.

        Args:
            version: Unique version identifier (e.g. ``"001"``).
            description: Human-readable description of the migration.
            operation: The migration operation to execute.

        Returns:
            Self for chaining.
        """
        self._pending.append((version, description, operation))
        return self

    async def get_applied_versions(self) -> set[str]:
        """Return the set of already-applied migration versions."""
        versions: set[str] = set()
        async for doc in self._migrations_col.find({}):  # type: ignore[attr-defined]
            versions.add(doc["version"])
        return versions

    async def migrate(self) -> list[str]:
        """Apply all pending migrations that haven't been applied yet.

        Returns:
            List of version strings that were applied.
        """
        applied = await self.get_applied_versions()
        newly_applied: list[str] = []

        # Sort by version string to ensure consistent ordering
        sorted_pending = sorted(self._pending, key=lambda x: x[0])

        for version, description, operation in sorted_pending:
            if version in applied:
                logger.debug(
                    "migration.skipped",
                    version=version,
                    description=description,
                )
                continue

            logger.info(
                "migration.applying",
                version=version,
                description=description,
            )

            await operation.execute(self._store)

            record = MigrationRecord(version=version, description=description)
            await self._migrations_col.insert_one(
                {
                    "version": record.version,
                    "description": record.description,
                    "applied_at": record.applied_at.isoformat(),
                }
            )

            newly_applied.append(version)
            logger.info(
                "migration.applied",
                version=version,
                description=description,
            )

        return newly_applied

    async def status(self) -> list[dict[str, Any]]:
        """Return migration status for all registered migrations.

        Returns:
            List of dicts with ``version``, ``description``, and ``applied`` status.
        """
        applied = await self.get_applied_versions()
        return [
            {
                "version": version,
                "description": description,
                "applied": version in applied,
            }
            for version, description, _ in sorted(self._pending, key=lambda x: x[0])
        ]


class MigrationOperation:
    """Base class for migration operations."""

    async def execute(self, store: DocumentStoreProtocol) -> None:
        """Execute the migration against the store."""
        raise NotImplementedError


__all__ = ["MigrationManager", "MigrationOperation", "MigrationRecord"]
