"""Database-per-tenant isolation strategy (reference implementation)."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.tenancy.errors import TenantError
from lexigram.result import Result


class DatabaseIsolationStrategy:
    """Full database isolation per tenant (reference implementation).

    This is a **reference implementation** that applications must subclass
    and extend with their infrastructure-specific provisioning logic
    (e.g. AWS RDS, GCP Cloud SQL).  It is NOT in
    ``IsolationStrategyRegistry.with_defaults()``.

    Attributes:
        name: ``"database"``
    """

    name: str = "database"

    async def apply_isolation(self, tenant_id: str, context: dict[str, Any]) -> None:
        """Record the tenant's database backend in the execution context.

        Args:
            tenant_id: The active tenant.
            context: Mutable execution context dict.
        """
        context["database_backend"] = f"tenant_{tenant_id}"

    async def remove_isolation(self, tenant_id: str) -> None:
        """No-op (connection routing resets with the request scope).

        Args:
            tenant_id: The tenant whose isolation context to remove.
        """

    async def provision_isolation(self, tenant_id: str) -> Result[None, TenantError]:
        """Provision a database for the tenant.

        Must be overridden by application subclasses with
        infrastructure-specific database creation logic.

        Args:
            tenant_id: The newly created tenant.

        Raises:
            NotImplementedError: Always — subclasses must override this.
        """
        raise NotImplementedError(
            "DatabaseIsolationStrategy.provision_isolation() must be overridden "
            "with infrastructure-specific database creation logic."
        )

    async def deprovision_isolation(self, tenant_id: str) -> Result[None, TenantError]:
        """Deprovision the tenant's database.

        Must be overridden by application subclasses.

        Args:
            tenant_id: The tenant being deactivated.

        Raises:
            NotImplementedError: Always — subclasses must override this.
        """
        raise NotImplementedError(
            "DatabaseIsolationStrategy.deprovision_isolation() must be overridden."
        )


__all__ = ["DatabaseIsolationStrategy"]
