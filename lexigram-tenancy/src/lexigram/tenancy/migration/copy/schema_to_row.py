"""Reference copy strategy — schema isolation to row-level isolation."""

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


class SchemaToRowCopy:
    """Copy strategy that migrates from schema to row-level isolation.

    Validates that the source isolation is ``"schema"`` and the target is
    ``"row_level"``, then delegates the actual data copy to a user-provided
    callable.

    Usage::

        strategy = SchemaToRowCopy(database=db_provider)
        result = await strategy.copy("tenant-abc", ctx)
    """

    def __init__(
        self,
        database: DatabaseProviderProtocol | None = None,
        copy_handler: CopyHandler | None = None,
    ) -> None:
        self._database = database
        self._copy_handler = copy_handler

    async def validate(self, tenant_id: str, context: MigrationContext) -> None:
        if context.source_strategy_name != "schema":
            raise ValueError(
                f"SchemaToRowCopy requires source 'schema', "
                f"got '{context.source_strategy_name}'"
            )
        if context.target_strategy_name != "row_level":
            raise ValueError(
                f"SchemaToRowCopy requires target 'row_level', "
                f"got '{context.target_strategy_name}'"
            )

    async def copy(self, tenant_id: str, context: MigrationContext) -> CopyResult:
        if self._copy_handler is not None:
            return await self._copy_handler(tenant_id, context)
        return CopyResult(
            records_copied=0,
            records_failed=0,
            source_snapshot=SnapshotResult(before_count=0, after_count=0),
            target_snapshot=SnapshotResult(before_count=0, after_count=0),
        )

    async def rollback(self, tenant_id: str, result: CopyResult) -> None:
        """No-op rollback (row-level data is cleaned up by saga compensation)."""


__all__ = ["SchemaToRowCopy"]
