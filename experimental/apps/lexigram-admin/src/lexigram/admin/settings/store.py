"""DB-backed store adapter bridging ConfigRegistry to tenant_configs."""

from __future__ import annotations

from collections.abc import Collection
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

    async def get(
        self, key: str, default: Any = None, tenant_id: str | None = None
    ) -> Any:
        """Retrieve a value by key, falling back to *default* when unset."""
        value = await self._service.get(tenant_id or self._tenant, key)
        return value if value is not None else default

    async def contains(self, key: str, tenant_id: str | None = None) -> bool | None:
        """Report whether the backing tenant store has an explicit key.

        Presence is intentionally separate from ``get``: a stored ``false``,
        ``0``, or empty string is still a configured override and must not be
        labelled as the node default in the settings UI.
        """
        probe = getattr(self._service, "contains", None)
        if not callable(probe):
            return None
        try:
            return await probe(tenant_id or self._tenant, key)
        except Exception:  # noqa: BLE001 — metadata is best-effort
            return None

    async def set(self, key: str, value: Any, tenant_id: str | None = None) -> None:
        """Persist a value by key."""
        await self._service.set(tenant_id or self._tenant, key, value)

    async def set_many(
        self, items: dict[str, Any], tenant_id: str | None = None
    ) -> None:
        """Persist several values atomically when the backend supports it.

        Prefers :meth:`AdminSettingsService.set_many`, which wraps the writes
        in a database transaction where one is available so a failure part-way
        through rolls the whole batch back. Services predating that method
        fall back to sequential writes, which are not atomic.
        """
        tenant = tenant_id or self._tenant
        batch = getattr(self._service, "set_many", None)
        if callable(batch):
            await batch(tenant, items)
            return
        for key, value in items.items():
            await self._service.set(tenant, key, value)

    async def set_many_if_unchanged(
        self,
        items: dict[str, Any],
        expected: dict[str, Any],
        tenant_id: str | None = None,
    ) -> None:
        """Persist several values only if storage still matches *expected*.

        Delegates to :meth:`AdminSettingsService.set_many_if_unchanged`, which
        re-checks inside the write transaction so a concurrent update is
        rejected instead of being overwritten.

        Raises:
            SettingsConflictError: If a concurrent change is detected.
        """
        tenant = tenant_id or self._tenant
        conditional = getattr(self._service, "set_many_if_unchanged", None)
        if callable(conditional):
            await conditional(tenant, items, expected)
            return
        await self.set_many(items, tenant_id=tenant)

    async def delete(self, key: str, tenant_id: str | None = None) -> None:
        """Remove a persisted setting while retaining its application default."""
        tenant = tenant_id or self._tenant
        delete = getattr(self._service, "delete", None)
        if not callable(delete):
            raise NotImplementedError("Settings service cannot remove values")
        await delete(tenant, key)

    async def apply_many(
        self,
        items: dict[str, Any],
        *,
        delete_keys: Collection[str] = frozenset(),
        expected: dict[str, Any] | None = None,
        tenant_id: str | None = None,
    ) -> None:
        """Apply writes and removals through one service transaction."""
        tenant = tenant_id or self._tenant
        apply = getattr(self._service, "apply_many_if_unchanged", None)
        if callable(apply) and expected is not None:
            await apply(tenant, items, delete_keys, expected)
            return
        if items:
            await self.set_many(items, tenant_id=tenant)
        if delete_keys:
            await self.delete_many(delete_keys, tenant_id=tenant)

    async def supports_conditional_write(self) -> bool:
        """Report whether the backing service enforces conditional writes."""
        probe = getattr(self._service, "supports_conditional_write", None)
        return bool(probe()) if callable(probe) else False
