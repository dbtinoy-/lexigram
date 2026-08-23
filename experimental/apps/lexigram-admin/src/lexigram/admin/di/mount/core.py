"""Core mount phases: resource resolution and the admin settings service."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.di.bundle_provider import AdminProvider
    from lexigram.admin.di.mount.context import MountContext

_log = get_logger(__name__)


class AdminMountCoreMixin:
    """Mount phases that resolve admin resources and settings plumbing."""

    # Host attributes provided by AdminProvider.
    _config: Any
    _resources: list[Any]
    _controllers: list[Any]
    _mount_failures: dict[str, str]
    _authorizer_service: Any

    _get_csrf_service: Any


    async def _mount_resources(
        self, resolver: Any, ctx: MountContext
    ) -> None:
        """Resolve registered resource classes into named instances.

        Failures are recorded in ``_mount_failures`` and re-raised only when
        strict resource resolution is configured.

        Args:
            resolver: The DI resolver for resource resolution.
            ctx: Mount pipeline state (``resources`` populated in place).
        """
        from lexigram.admin.rbac.inventory import PermissionInventoryService

        for resource_cls in self._resources:
            name = (
                getattr(resource_cls, "name", None)
                or resource_cls.__name__.replace("Resource", "").lower()
            )
            try:
                ctx.resources[name] = await resolver.resolve(
                    resource_cls,
                    bypass_visibility=True,
                )
            except Exception as exc:
                _log.error(
                    "admin.resource_resolution_failed",
                    resource=resource_cls.__name__,
                    error=str(exc),
                    strict=self._config.strict_resource_resolution,
                )
                self._mount_failures[f"resource:{resource_cls.__name__}"] = str(exc)
                if self._config.strict_resource_resolution:
                    raise

        # Populate the RBAC permission inventory from registered resources
        try:
            inventory = await resolver.resolve(
                PermissionInventoryService,
                bypass_visibility=True,
            )
            inventory.register_resources(ctx.resources.keys())
        except Exception as exc:  # noqa: BLE001 — discovery is best-effort
            _log.warning(
                "admin.rbac_inventory_discovery_failed",
                error=str(exc),
            )

    async def _mount_settings_service(
        self, resolver: Any, ctx: MountContext
    ) -> None:
        """Create the shared settings service for runtime theme overrides.

        Best-effort: without a database provider the service falls back to an
        in-memory instance so the panel still mounts.

        Args:
            resolver: The DI resolver for settings dependencies.
            ctx: Mount pipeline state (``settings_service`` populated).
        """
        admin_settings_service: Any = None
        try:
            from lexigram.admin.services.settings_service import (
                AdminSettingsDbProvider,
                AdminSettingsService,
            )
            from lexigram.contracts.data import DatabaseProviderProtocol

            db_provider = await resolver.resolve(
                DatabaseProviderProtocol,
                bypass_visibility=True,
            )
            config_provider = AdminSettingsDbProvider(db=db_provider)
            # Ensure the tenant_configs table is created eagerly at startup
            try:
                await config_provider._ensure_table()
            except Exception:
                _log.warning("admin.tenant_config_table_creation_failed")
            admin_settings_service = AdminSettingsService(
                config_provider=config_provider,
            )
            from lexigram.admin.settings.panel.registry import ConfigRegistry
            from lexigram.admin.settings.store import TenantConfigStore

            try:
                registry = await resolver.resolve(
                    ConfigRegistry,
                    bypass_visibility=True,
                )
                registry.register_store("db", TenantConfigStore(admin_settings_service))
            except Exception:
                _log.warning("admin.settings_store_registration_failed")
        except Exception:
            try:
                admin_settings_service = AdminSettingsService()
            except Exception as exc:  # noqa: BLE001 — fallback is best-effort
                _log.warning("admin.settings_service_fallback_failed", reason=str(exc))
        ctx.settings_service = admin_settings_service
