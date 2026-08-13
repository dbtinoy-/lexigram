"""Per-tenant configuration service with defaults and event emission."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lexigram.contracts.events.protocols import DomainEventPublisherProtocol
from lexigram.contracts.tenancy.events import TenantConfigChanged
from lexigram.contracts.tenancy.protocols import TenantConfigProviderProtocol
from lexigram.logging import get_logger

logger = get_logger(__name__)


class TenantConfigService:
    """High-level per-tenant configuration service.

    Combines a raw :class:`~lexigram.contracts.tenancy.protocols.TenantConfigProviderProtocol`
    backend with a defaults dict and event emission.

    Priority order for :meth:`get`:
    1. Tenant-specific override from the provider.
    2. Application default from ``defaults``.
    3. ``None``.

    Usage::

        service = TenantConfigService(provider, defaults={"max_users": 50}, event_bus=bus)
        value = await service.get("tenant-abc", "max_users")
    """

    def __init__(
        self,
        config_provider: TenantConfigProviderProtocol,
        defaults: dict[str, Any],
        event_bus: DomainEventPublisherProtocol,
    ) -> None:
        """Initialise the service.

        Args:
            config_provider: Underlying key-value config backend.
            defaults: Application-level default values used when no tenant
                override is set.
            event_bus: Event bus for publishing
                :class:`~lexigram.contracts.tenancy.events.TenantConfigChanged`
                events.
        """
        self._provider = config_provider
        self._defaults = defaults
        self._event_bus = event_bus

    async def get(self, tenant_id: str, key: str) -> Any:
        """Get a config value with fallback to defaults.

        Args:
            tenant_id: The tenant whose config is queried.
            key: Configuration key.

        Returns:
            The tenant override if set, otherwise the application default,
            otherwise ``None``.
        """
        value = await self._provider.get_config(tenant_id, key)
        if value is not None:
            return value
        return self._defaults.get(key)

    async def set(self, tenant_id: str, key: str, value: Any) -> None:
        """Set a config value and publish the change event.

        Args:
            tenant_id: The tenant whose config is updated.
            key: Configuration key.
            value: New value.
        """
        old_value = await self._provider.get_config(tenant_id, key)
        await self._provider.set_config(tenant_id, key, value)
        await self._event_bus.publish(
            TenantConfigChanged(
                tenant_id=tenant_id,
                key=key,
                old_value=old_value,
                new_value=value,
                timestamp=datetime.now(UTC),
            )
        )
        logger.debug("tenant_config_set", tenant_id=tenant_id, key=key)

    async def get_effective_config(self, tenant_id: str) -> dict[str, Any]:
        """Merge defaults with tenant overrides (tenant wins on conflict).

        Args:
            tenant_id: The tenant whose effective config is computed.

        Returns:
            A merged dict where tenant overrides take precedence over defaults.
        """
        overrides = await self._provider.get_all_config(tenant_id)
        return {**self._defaults, **overrides}


__all__ = ["TenantConfigService"]
