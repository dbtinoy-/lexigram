"""Mount phase that resolves and wires every admin controller."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.di.bundle_provider import AdminProvider
    from lexigram.admin.di.mount.context import MountContext

_log = get_logger(__name__)


class AdminMountControllersMixin:
    """Resolves built-in admin controllers and wires their private services."""

    async def _mount_controllers(
        self: AdminProvider, resolver: Any, ctx: MountContext
    ) -> None:
        """Resolve every built-in controller, best-effort per controller.

        Failures are recorded in ``_mount_failures`` and only abort the mount
        when strict resource resolution is configured. Controllers receive
        runtime wiring (settings, audit, CSRF, user store) as available.

        Args:
            resolver: The DI resolver for controller resolution.
            ctx: Mount pipeline state (``controllers`` populated in place).
        """
        # Create shared settings_service for runtime theme overrides (best-effort)
        admin_settings_service = ctx.settings_service

        for controller_cls in self._controllers:
            try:
                instance = await resolver.resolve(
                    controller_cls,
                    bypass_visibility=True,
                )
                ctx.controllers.append(instance)
                if admin_settings_service is not None and hasattr(
                    instance, "_settings_service"
                ):
                    instance._settings_service = admin_settings_service
            except Exception as exc:
                _log.error(
                    "admin.controller_resolution_failed",
                    controller=controller_cls.__name__,
                    error=str(exc),
                    strict=self._config.strict_resource_resolution,
                )
                self._mount_failures[f"controller:{controller_cls.__name__}"] = str(exc)
                if self._config.strict_resource_resolution:
                    raise

        # Resolve built-in WidgetController (best-effort)
        try:
            from lexigram.admin.auth.protocols import (
                AdminAuditLogServiceProtocol,
            )
            from lexigram.admin.controllers.widgets import WidgetController

            widget_controller = await resolver.resolve(
                WidgetController,
                bypass_visibility=True,
            )
            ctx.controllers.append(widget_controller)
            if admin_settings_service is not None and hasattr(
                widget_controller, "_settings_service"
            ):
                widget_controller._settings_service = admin_settings_service
            try:
                audit_service = await resolver.resolve(
                    AdminAuditLogServiceProtocol,
                    bypass_visibility=True,
                )
            except Exception:
                audit_service = None
            if audit_service is not None and hasattr(
                widget_controller, "_audit_service"
            ):
                widget_controller._audit_service = audit_service
            csrf_service = await self._get_csrf_service(resolver)
            if hasattr(widget_controller, "_csrf_service"):
                widget_controller._csrf_service = csrf_service
        except Exception as exc:
            _log.error(
                "admin.widget_controller_resolution_failed",
                error=str(exc),
                strict=self._config.strict_resource_resolution,
            )
            self._mount_failures["controller:WidgetController"] = str(exc)
            if self._config.strict_resource_resolution:
                raise

        # Resolve built-in DashboardController (best-effort)
        try:
            from lexigram.admin.controllers.dashboard import DashboardController

            dashboard_controller = await resolver.resolve(
                DashboardController,
                bypass_visibility=True,
            )
            ctx.controllers.append(dashboard_controller)
            if admin_settings_service is not None:
                dashboard_controller._settings_service = admin_settings_service
        except Exception as exc:
            _log.error(
                "admin.dashboard_controller_resolution_failed",
                error=str(exc),
                strict=self._config.strict_resource_resolution,
            )
            self._mount_failures["controller:DashboardController"] = str(exc)
            if self._config.strict_resource_resolution:
                raise

        # Resolve built-in AuthController (login, logout)
        try:
            from lexigram.admin.controllers.auth import AuthController

            auth_controller = await resolver.resolve(
                AuthController,
                bypass_visibility=True,
            )
            ctx.controllers.append(auth_controller)
            if admin_settings_service is not None:
                auth_controller._settings_service = admin_settings_service

            # Wire self-service registration (opt-in via config). Best-effort:
            # without a resolvable user store, registration stays disabled.
            try:
                from lexigram.admin.auth.store.protocols import (
                    AdminUserStoreProtocol,
                )

                auth_controller._user_store = await resolver.resolve(
                    AdminUserStoreProtocol,
                    bypass_visibility=True,
                )
            except Exception:
                auth_controller._user_store = None
            registration = getattr(self._config.auth, "registration", None)
            auth_controller._registration_enabled = bool(
                registration and registration.enabled
            )
            auth_controller._registration_default_role = (
                str(registration.default_role) if registration else "admin"
            )
            auth_controller._registration_domains = (
                list(registration.allowed_email_domains) if registration else []
            )
        except Exception as exc:
            _log.error(
                "admin.auth_controller_resolution_failed",
                error=str(exc),
                strict=self._config.strict_resource_resolution,
            )
            self._mount_failures["controller:AuthController"] = str(exc)
            if self._config.strict_resource_resolution:
                raise

        # Resolve built-in ProfileController (profile page, password change)
        try:
            from lexigram.admin.controllers.profile import ProfileController

            profile_controller = await resolver.resolve(
                ProfileController,
                bypass_visibility=True,
            )
            ctx.controllers.append(profile_controller)
            if admin_settings_service is not None:
                profile_controller._settings_service = admin_settings_service
            try:
                from lexigram.admin.auth.store.protocols import (
                    AdminUserStoreProtocol,
                )

                profile_controller._user_store = await resolver.resolve(
                    AdminUserStoreProtocol,
                    bypass_visibility=True,
                )
            except Exception:
                profile_controller._user_store = None
        except Exception as exc:
            _log.error(
                "admin.profile_controller_resolution_failed",
                error=str(exc),
                strict=self._config.strict_resource_resolution,
            )
            self._mount_failures["controller:ProfileController"] = str(exc)
            if self._config.strict_resource_resolution:
                raise

        # Resolve built-in SetupController (first-run wizard)
        try:
            from lexigram.admin.controllers.setup import SetupController

            setup_controller = await resolver.resolve(
                SetupController,
                bypass_visibility=True,
            )
            ctx.controllers.append(setup_controller)
            if admin_settings_service is not None:
                setup_controller._settings_service = admin_settings_service
        except Exception as exc:
            _log.error(
                "admin.setup_controller_resolution_failed",
                error=str(exc),
                strict=self._config.strict_resource_resolution,
            )
            self._mount_failures["controller:SetupController"] = str(exc)
            if self._config.strict_resource_resolution:
                raise

        # Mount ErrorController (styled error pages) — best-effort
        try:
            from lexigram.admin.controllers.error import ErrorController

            error_controller = await resolver.resolve(
                ErrorController,
                bypass_visibility=True,
            )
            ctx.controllers.append(error_controller)
        except Exception as exc:
            _log.error(
                "admin.error_controller_resolution_failed",
                error=str(exc),
                strict=self._config.strict_resource_resolution,
            )
            self._mount_failures["controller:ErrorController"] = str(exc)
            if self._config.strict_resource_resolution:
                raise

        # Mount PoolHealthController (connection pool monitoring) — best-effort.
        # pool_manager/task_manager are optional: without them the endpoints
        # respond 503 instead of failing resolution.
        try:
            from lexigram.admin.controllers.pool_health import PoolHealthController

            pool_health_controller = await resolver.resolve(
                PoolHealthController,
                bypass_visibility=True,
            )
            ctx.controllers.append(pool_health_controller)
        except Exception as exc:
            _log.error(
                "admin.pool_health_controller_resolution_failed",
                error=str(exc),
                strict=self._config.strict_resource_resolution,
            )
            self._mount_failures["controller:PoolHealthController"] = str(exc)
            if self._config.strict_resource_resolution:
                raise

        # Mount ProgressController (SSE/status progress tracking) — best-effort.
        # Tries an integrator-registered tracker first; falls back to the
        # admin-owned LocalProgressTracker (no dependency on optional
        # integration packages — without one the controller mounts with the
        # in-process tracker instead of being skipped).
        try:
            from lexigram.admin.controllers.progress import (
                LocalProgressTracker,
                ProgressController,
            )

            try:
                progress_controller = await resolver.resolve(
                    ProgressController,
                    bypass_visibility=True,
                )
            except Exception:
                progress_controller = ProgressController(tracker=LocalProgressTracker())
            ctx.controllers.append(progress_controller)
        except ModuleNotFoundError as exc:
            _log.info(
                "admin.progress_controller_skipped",
                reason="progress_controller_unavailable",
                error=str(exc),
            )
        except Exception as exc:
            _log.error(
                "admin.progress_controller_resolution_failed",
                error=str(exc),
                strict=self._config.strict_resource_resolution,
            )
            self._mount_failures["controller:ProgressController"] = str(exc)
            if self._config.strict_resource_resolution:
                raise

        # Mount SettingsController (theme & branding settings)
        try:
            from lexigram.admin.auth.protocols import (
                AdminAuditLogServiceProtocol,
            )
            from lexigram.admin.controllers.settings import SettingsController
            from lexigram.admin.engine.renderer import AdminRenderer
            from lexigram.admin.settings.panel.registry import ConfigRegistry

            settings_csrf = await self._get_csrf_service(resolver)

            settings_registry: ConfigRegistry | None = None
            try:
                settings_registry = await resolver.resolve(
                    ConfigRegistry,
                    bypass_visibility=True,
                )
            except Exception as exc:  # noqa: BLE001 — settings registry is optional
                _log.warning("admin.config_registry_unavailable", reason=str(exc))

            settings_audit: AdminAuditLogServiceProtocol | None = None
            try:
                settings_audit = await resolver.resolve(
                    AdminAuditLogServiceProtocol,
                    bypass_visibility=True,
                )
            except Exception as exc:  # noqa: BLE001 — audit service is optional
                _log.warning("admin.audit_service_unavailable", reason=str(exc))

            renderer = await resolver.resolve(
                AdminRenderer,
                bypass_visibility=True,
            )
            settings_controller = SettingsController(
                renderer=renderer,
                settings_service=admin_settings_service,
                csrf_service=settings_csrf,
                audit_service=settings_audit,
                registry=settings_registry,
                rbac_config=self._config.rbac,
            )
            ctx.controllers.append(settings_controller)
        except Exception as exc:
            _log.warning(
                "admin.settings_controller_skipped",
                error=str(exc),
            )

        # Mount InfrastructureController (cluster landing page)
        try:
            from lexigram.admin.clusters import Cluster, ClusterRegistry
            from lexigram.admin.controllers.clusters import ClusterCenterController
            from lexigram.admin.controllers.infrastructure import (
                InfrastructureController,
            )
            from lexigram.admin.engine.renderer import AdminRenderer

            infra_renderer = await resolver.resolve(
                AdminRenderer,
                bypass_visibility=True,
            )
            ctx.controllers.append(InfrastructureController(renderer=infra_renderer))

            # Build the cluster registry (built-in + config-declared extras)
            # and mount a generic center controller per extra cluster.
            cluster_registry = ClusterRegistry.with_defaults()
            extra_specs = getattr(self._config, "clusters", None)
            for spec in (extra_specs.extra if extra_specs else []) or []:
                cluster = Cluster(
                    name=spec.name,
                    label=spec.label,
                    icon=spec.icon,
                    order=spec.order,
                    collapsible=spec.collapsible,
                    collapsed_by_default=spec.collapsed_by_default,
                    slug=spec.slug,
                    group=spec.group,
                    description=spec.description,
                )
                cluster_registry.register(cluster)
                ctx.controllers.append(
                    ClusterCenterController(
                        renderer=infra_renderer,
                        cluster=cluster,
                    )
                )
            ctx.cluster_registry = cluster_registry
        except Exception as exc:
            _log.warning(
                "admin.infrastructure_controller_skipped",
                error=str(exc),
            )

        # Mount PluginsController (plugin listing & toggles) — best-effort.
        try:
            from lexigram.admin.auth.protocols import (
                AdminAuditLogServiceProtocol,
            )
            from lexigram.admin.controllers.plugins import PluginsController
            from lexigram.admin.engine.renderer import AdminRenderer

            plugins_csrf_service = await self._get_csrf_service(resolver)

            plugins_audit_service: AdminAuditLogServiceProtocol | None = None
            try:
                plugins_audit_service = await resolver.resolve(
                    AdminAuditLogServiceProtocol,
                    bypass_visibility=True,
                )
            except Exception as exc:  # noqa: BLE001 — audit service is optional
                _log.warning("admin.audit_service_unavailable", reason=str(exc))

            plugins_renderer = await resolver.resolve(
                AdminRenderer,
                bypass_visibility=True,
            )
            ctx.controllers.append(
                PluginsController(
                    renderer=plugins_renderer,
                    csrf_service=plugins_csrf_service,
                    audit_service=plugins_audit_service,
                    rbac_config=self._config.rbac,
                )
            )
        except Exception as exc:
            _log.warning(
                "admin.plugins_controller_skipped",
                error=str(exc),
            )
