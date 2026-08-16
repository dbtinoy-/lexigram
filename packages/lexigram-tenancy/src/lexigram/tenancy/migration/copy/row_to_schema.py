"""Reference copy strategy — row-level isolation to schema isolation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from lexigram.contracts.tenancy.migration import (
    CopyResult,
    MigrationContext,
    SnapshotResult,
)

if TYPE_CHECKING:
    from lexigram.contracts.data.sql.database import DatabaseProviderProtocol

CopyHandler = Callable[[str, MigrationContext], Awaitable[CopyResult]]
"""Signature for application-provided data-copy callables."""


class RowToSchemaCopy:
    """Copy strategy that migrates from row-level to schema isolation.

    Validates that the source isolation is ``"row_level"`` and the target is
    ``"schema"``, then delegates the actual data copy to a user-provided
    callable.

    Usage::

        strategy = RowToSchemaCopy(database=db_provider)
        result = await strategy.copy("tenant-abc", ctx)
    """

    def __init__(
        self,
        database: DatabaseProviderProtocol | None = None,
        copy_handler: CopyHandler | None = None,
    ) -> None:
        """Initialise the strategy.

        Args:
            database: Optional database provider for SQL operations.
            copy_handler: Optional application-specific copy callable.
                When omitted the strategy validates infrastructure only.
        """
        self._database = database
        self._copy_handler = copy_handler

    async def validate(self, tenant_id: str, context: MigrationContext) -> None:
        """Verify source is row-level and target is schema.

        Args:
            tenant_id: The tenant identifier.
            context: Migration context with source/target details.

        Raises:
            ValueError: If the migration is not row→schema.
        """
        if context.source_strategy_name != "row_level":
            raise ValueError(
                f"RowToSchemaCopy requires source 'row_level', "
                f"got '{context.source_strategy_name}'"
            )
        if context.target_strategy_name != "schema":
            raise ValueError(
                f"RowToSchemaCopy requires target 'schema', "
                f"got '{context.target_strategy_name}'"
            )

    async def copy(self, tenant_id: str, context: MigrationContext) -> CopyResult:
        """Execute the row→schema copy.

        Delegates to the configured *copy_handler* if provided; otherwise
        returns an empty result (infrastructure-only validation mode).

        Args:
            tenant_id: The tenant identifier.
            context: Migration context.

        Returns:
            A ``CopyResult`` summarising the operation.

        Raises:
            RuntimeError: If the copy handler fails.
        """
        if self._copy_handler is not None:
            return await self._copy_handler(tenant_id, context)
        return CopyResult(
            records_copied=0,
            records_failed=0,
            source_snapshot=SnapshotResult(before_count=0, after_count=0),
            target_snapshot=SnapshotResult(before_count=0, after_count=0),
        )

    async def rollback(self, tenant_id: str, result: CopyResult) -> None:
        """No-op rollback (schema is cleaned up by saga compensation).

        Args:
            tenant_id: The tenant identifier.
            result: The ``CopyResult`` from the copy operation.
        """


__all__ = ["RowToSchemaCopy"]
