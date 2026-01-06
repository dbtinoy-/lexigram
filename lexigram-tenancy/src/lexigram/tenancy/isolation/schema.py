"""Schema-per-tenant isolation strategy (reference implementation)."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any

from lexigram.contracts.tenancy.errors import TenantError, TenantProvisioningError
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol


class SchemaIsolationStrategy:
    """Creates a PostgreSQL schema per tenant.

    This is a **reference implementation**.  Applications must register it
    explicitly — it is NOT in ``IsolationStrategyRegistry.with_defaults()``.

    Requires ``lexigram-tenancy[sql]``.  Applications that need it must also
    configure the deprovision policy appropriate for their infrastructure.

    Attributes:
        name: ``"schema"``
    """

    name: str = "schema"

    def __init__(
        self,
        db_provider: DatabaseProviderProtocol,
        deprovision_policy: str = "rename",
    ) -> None:
        """Initialise the strategy.

        Args:
            db_provider: Database provider implementing
                :class:`~lexigram.contracts.data.DatabaseProviderProtocol`.
            deprovision_policy: ``"rename"`` (archive schema, default) or
                ``"drop"`` (permanently destroy).
        """
        self._db = db_provider
        self._deprovision_policy = deprovision_policy

    async def provision_isolation(self, tenant_id: str) -> Result[None, TenantError]:
        """Create a PostgreSQL schema for the tenant.

        Args:
            tenant_id: The newly created tenant.

        Returns:
            ``Ok(None)`` on success, ``Err(TenantProvisioningError)`` if the
            ``tenant_id`` contains characters that are unsafe for schema names.
        """
        if not re.match(r"^[a-zA-Z0-9_]+$", tenant_id):
            return Err(
                TenantProvisioningError(
                    f"Invalid tenant_id for schema name: {tenant_id}"
                )
            )
        schema_name = f"tenant_{tenant_id}"
        async with self._db.scoped_context() as ctx:
            await ctx.execute_raw(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")  # noqa: S608
        return Ok(None)

    async def apply_isolation(self, tenant_id: str, context: dict[str, Any]) -> None:
        """Set the PostgreSQL ``search_path`` in the execution context.

        Args:
            tenant_id: The active tenant.
            context: Mutable execution context dict.
        """
        context["search_path"] = f"tenant_{tenant_id}"

    async def remove_isolation(self, tenant_id: str) -> None:
        """No-op (search_path resets with the DB connection).

        Args:
            tenant_id: The tenant whose isolation context to remove.
        """

    async def deprovision_isolation(self, tenant_id: str) -> Result[None, TenantError]:
        """Drop or rename the tenant schema.

        Args:
            tenant_id: The tenant being deactivated.

        Returns:
            ``Ok(None)`` on success.
        """
        schema_name = f"tenant_{tenant_id}"
        if self._deprovision_policy == "drop":
            async with self._db.scoped_context() as ctx:
                await ctx.execute_raw(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")  # noqa: S608
        elif self._deprovision_policy == "rename":
            archived = f"archived_{tenant_id}_{int(time.time())}"
            async with self._db.scoped_context() as ctx:
                await ctx.execute_raw(  # noqa: S608
                    f"ALTER SCHEMA {schema_name} RENAME TO {archived}"
                )
        return Ok(None)


__all__ = ["SchemaIsolationStrategy"]
