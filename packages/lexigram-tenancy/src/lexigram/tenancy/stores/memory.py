"""In-memory tenant provider — for testing and development."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from lexigram.contracts.tenancy.commands import CreateTenantCommand, UpdateTenantCommand
from lexigram.contracts.tenancy.errors import TenantError, TenantNotFoundError
from lexigram.contracts.tenancy.types import TenantInfo, TenantStatus
from lexigram.result import Err, Ok, Result


class InMemoryTenantProvider:
    """Dict-backed tenant store implementing both
    :class:`~lexigram.contracts.tenancy.protocols.TenantProviderProtocol` and
    :class:`~lexigram.contracts.tenancy.protocols.TenantConfigProviderProtocol`.

    Suitable for unit testing, integration testing, and single-process
    development environments.  Not suitable for production multi-process
    deployments (state is not shared across processes).

    A single instance acts as both the tenant store and the config store,
    so only one registration is needed in the DI container.
    """

    def __init__(self) -> None:
        """Initialise empty tenant and config stores."""
        self._tenants: dict[str, TenantInfo] = {}
        self._configs: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # TenantProviderProtocol
    # ------------------------------------------------------------------

    async def get_tenant(self, tenant_id: str) -> TenantInfo | None:
        """Return the tenant record for *tenant_id*, or ``None``.

        Args:
            tenant_id: Unique tenant identifier.

        Returns:
            :class:`~lexigram.contracts.tenancy.types.TenantInfo` or ``None``.
        """
        return self._tenants.get(tenant_id)

    async def get_tenant_by_slug(self, slug: str) -> TenantInfo | None:
        """Return the tenant with the given slug, or ``None``.

        Args:
            slug: URL-safe tenant identifier.

        Returns:
            :class:`~lexigram.contracts.tenancy.types.TenantInfo` or ``None``.
        """
        return next((t for t in self._tenants.values() if t.slug == slug), None)

    async def list_tenants(self, *, active_only: bool = True) -> list[TenantInfo]:
        """List tenants, optionally filtering to active ones.

        Args:
            active_only: Return only active tenants when ``True``.

        Returns:
            List of :class:`~lexigram.contracts.tenancy.types.TenantInfo`.
        """
        tenants = list(self._tenants.values())
        if active_only:
            return [t for t in tenants if t.status == TenantStatus.ACTIVE]
        return tenants

    async def create_tenant(
        self, command: CreateTenantCommand
    ) -> Result[TenantInfo, TenantError]:
        """Create and persist a new tenant record.

        Args:
            command: Creation parameters.

        Returns:
            ``Ok(TenantInfo)`` always (in-memory store never fails).
        """
        tenant_id = str(uuid4())
        info = TenantInfo(
            tenant_id=tenant_id,
            slug=command.slug,
            name=command.name,
            status=TenantStatus.ACTIVE,
            plan=command.plan,
            config=command.config,
            metadata=command.metadata,
            created_at=datetime.now(UTC),
        )
        self._tenants[tenant_id] = info
        return Ok(info)

    async def update_tenant(
        self, tenant_id: str, command: UpdateTenantCommand
    ) -> Result[TenantInfo, TenantError]:
        """Update mutable fields on an existing tenant.

        Args:
            tenant_id: Identifier of the tenant to update.
            command: Fields to apply (``None`` fields are skipped).

        Returns:
            ``Ok(TenantInfo)`` on success, ``Err(TenantNotFoundError)`` if not found.
        """
        existing = self._tenants.get(tenant_id)
        if existing is None:
            return Err(TenantNotFoundError(tenant_id))
        updated = TenantInfo(
            tenant_id=existing.tenant_id,
            slug=existing.slug,
            name=command.name if command.name is not None else existing.name,
            status=existing.status,
            plan=command.plan if command.plan is not None else existing.plan,
            config=command.config if command.config is not None else existing.config,
            metadata=command.metadata
            if command.metadata is not None
            else existing.metadata,
            created_at=existing.created_at,
        )
        self._tenants[tenant_id] = updated
        return Ok(updated)

    async def deactivate_tenant(self, tenant_id: str) -> Result[None, TenantError]:
        """Mark a tenant as inactive.

        Args:
            tenant_id: Identifier of the tenant to deactivate.

        Returns:
            ``Ok(None)`` on success, ``Err(TenantNotFoundError)`` if not found.
        """
        existing = self._tenants.get(tenant_id)
        if existing is None:
            return Err(TenantNotFoundError(tenant_id))
        self._tenants[tenant_id] = TenantInfo(
            tenant_id=existing.tenant_id,
            slug=existing.slug,
            name=existing.name,
            status=TenantStatus.INACTIVE,
            plan=existing.plan,
            config=existing.config,
            metadata=existing.metadata,
            created_at=existing.created_at,
        )
        return Ok(None)

    async def activate_tenant(self, tenant_id: str) -> Result[None, TenantError]:
        """Mark a tenant as active.

        Args:
            tenant_id: Identifier of the tenant to activate.

        Returns:
            ``Ok(None)`` on success, ``Err(TenantNotFoundError)`` if not found.
        """
        existing = self._tenants.get(tenant_id)
        if existing is None:
            return Err(TenantNotFoundError(tenant_id))
        self._tenants[tenant_id] = TenantInfo(
            tenant_id=existing.tenant_id,
            slug=existing.slug,
            name=existing.name,
            status=TenantStatus.ACTIVE,
            plan=existing.plan,
            config=existing.config,
            metadata=existing.metadata,
            created_at=existing.created_at,
        )
        return Ok(None)

    async def suspend_tenant(
        self, tenant_id: str, reason: str | None = None
    ) -> Result[None, TenantError]:
        """Mark a tenant as suspended.

        Args:
            tenant_id: Identifier of the tenant to suspend.
            reason: Optional reason string (stored in metadata for reference).

        Returns:
            ``Ok(None)`` on success, ``Err(TenantNotFoundError)`` if not found.
        """
        existing = self._tenants.get(tenant_id)
        if existing is None:
            return Err(TenantNotFoundError(tenant_id))
        meta = dict(existing.metadata)
        if reason:
            meta["suspension_reason"] = reason
        self._tenants[tenant_id] = TenantInfo(
            tenant_id=existing.tenant_id,
            slug=existing.slug,
            name=existing.name,
            status=TenantStatus.SUSPENDED,
            plan=existing.plan,
            config=existing.config,
            metadata=meta,
            created_at=existing.created_at,
        )
        return Ok(None)

    # ------------------------------------------------------------------
    # TenantConfigProviderProtocol
    # ------------------------------------------------------------------

    async def get_config(self, tenant_id: str, key: str) -> Any | None:
        """Retrieve a single config value for a tenant.

        Args:
            tenant_id: The tenant whose config is queried.
            key: Configuration key.

        Returns:
            The value if set, or ``None``.
        """
        return self._configs.get(tenant_id, {}).get(key)

    async def get_all_config(self, tenant_id: str) -> dict[str, Any]:
        """Retrieve all config for a tenant.

        Args:
            tenant_id: The tenant whose config is retrieved.

        Returns:
            A copy of the tenant's config dict (empty dict if none set).
        """
        return dict(self._configs.get(tenant_id, {}))

    async def set_config(self, tenant_id: str, key: str, value: Any) -> None:
        """Set a config value for a tenant.

        Args:
            tenant_id: The tenant whose config is updated.
            key: Configuration key.
            value: New value.
        """
        if tenant_id not in self._configs:
            self._configs[tenant_id] = {}
        self._configs[tenant_id][key] = value


__all__ = ["InMemoryTenantProvider"]
