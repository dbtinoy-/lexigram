"""Tenant provisioner — orchestrates isolation on create/remove."""

from __future__ import annotations

from lexigram.contracts.tenancy.errors import TenantError
from lexigram.contracts.tenancy.protocols import TenantIsolationStrategyProtocol
from lexigram.logging import get_logger
from lexigram.result import Ok, Result

logger = get_logger(__name__)


class TenantProvisioner:
    """Orchestrates data isolation setup and teardown when tenants are
    created or deactivated.

    When ``auto_provision`` is ``False`` (e.g. in tests), both
    :meth:`provision` and :meth:`deprovision` are no-ops that immediately
    return ``Ok(None)``.
    """

    def __init__(
        self,
        strategy: TenantIsolationStrategyProtocol,
        auto_provision: bool = True,
    ) -> None:
        """Initialise the provisioner.

        Args:
            strategy: The isolation strategy to use for provisioning.
            auto_provision: When ``False``, skip provisioning entirely.
                Useful for testing.
        """
        self._strategy = strategy
        self._auto_provision = auto_provision

    async def provision(self, tenant_id: str) -> Result[None, TenantError]:
        """Provision isolation resources for a new tenant.

        Args:
            tenant_id: The newly created tenant.

        Returns:
            ``Ok(None)`` on success (or when ``auto_provision=False``),
            ``Err(TenantError)`` on failure.
        """
        if not self._auto_provision:
            return Ok(None)
        logger.debug(
            "provisioning_tenant", tenant_id=tenant_id, strategy=self._strategy.name
        )
        return await self._strategy.provision_isolation(tenant_id)

    async def deprovision(self, tenant_id: str) -> Result[None, TenantError]:
        """Deprovision isolation resources for a deactivated tenant.

        Args:
            tenant_id: The tenant being deactivated.

        Returns:
            ``Ok(None)`` on success (or when ``auto_provision=False``),
            ``Err(TenantError)`` on failure.
        """
        if not self._auto_provision:
            return Ok(None)
        logger.debug(
            "deprovisioning_tenant", tenant_id=tenant_id, strategy=self._strategy.name
        )
        return await self._strategy.deprovision_isolation(tenant_id)


__all__ = ["TenantProvisioner"]
