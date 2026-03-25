"""DB-backed store adapter bridging ConfigRegistry to tenant_configs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.settings.panel.registry import StoreBase

if TYPE_CHECKING:
    from lexigram.admin.services.settings_service import AdminSettingsService

__all__ = ["TenantConfigStore"]

DEFAULT_TENANT = "default"


class TenantConfigStore(StoreBase):
    """StoreBase implementation persisting to tenant_configs.

    Keys are stored verbatim (e.g. ``admin.cache.enabled``) via
    ``AdminSettingsService``, which prefixes them with ``admin_ui.`` in the
    ``tenant_configs`` table.
    """

    def __init__(
        self,
        service: AdminSettingsService,
        tenant_id: str = DEFAULT_TENANT,
    ) -> None:
        self._service = service
        self._tenant = tenant_id

    async def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value by key, falling back to *default* when unset."""
        value = await self._service.get(self._tenant, key)
        return value if value is not None else default

    async def set(self, key: str, value: Any) -> None:
        """Persist a value by key."""
        await self._service.set(self._tenant, key, value)
