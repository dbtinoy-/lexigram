"""CLI shell context factories for lexigram-tenancy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.tenancy.lifecycle.service import TenantLifecycleService

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


async def provide_tenant_service(
    container: ContainerResolverProtocol,
) -> TenantLifecycleService:
    """Provide TenantLifecycleService for interactive shell use.

    Args:
        container: Booted DI container.

    Returns:
        The resolved TenantLifecycleService instance.
    """
    return await container.resolve(TenantLifecycleService)
