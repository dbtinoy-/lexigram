"""Row-level isolation strategy (default, no-op provisioning)."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.tenancy.errors import TenantError
from lexigram.contracts.tenancy.types import (
    TenantResolutionContext,  # noqa: F401 - kept for completeness
)
from lexigram.result import Ok, Result


class RowLevelIsolationStrategy:
    """Row-level isolation strategy.

    Provisioning is a no-op because isolation is enforced at query time by
    ``lexigram-sql``'s ``multi_tenant=True`` flag and ``TenantScope`` query
    scope rather than by separate schema/database resources.

    Attributes:
        name: ``"row_level"``
    """

    name: str = "row_level"

    async def apply_isolation(self, tenant_id: str, context: dict[str, Any]) -> None:
        """No-op — isolation is handled at the ORM/query level.

        Args:
            tenant_id: The active tenant.
            context: Execution context dict (not modified).
        """

    async def remove_isolation(self, tenant_id: str) -> None:
        """No-op.

        Args:
            tenant_id: The tenant whose isolation context to remove.
        """

    async def provision_isolation(self, tenant_id: str) -> Result[None, TenantError]:
        """No-op provisioning — nothing to create for row-level isolation.

        Args:
            tenant_id: The newly created tenant.

        Returns:
            ``Ok(None)`` always.
        """
        return Ok(None)

    async def deprovision_isolation(self, tenant_id: str) -> Result[None, TenantError]:
        """No-op deprovisioning.

        Args:
            tenant_id: The tenant being deactivated.

        Returns:
            ``Ok(None)`` always.
        """
        return Ok(None)


__all__ = ["RowLevelIsolationStrategy"]
