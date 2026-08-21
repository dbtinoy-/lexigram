"""Admin bundle provider — orchestrates focused sub-providers.

Follows the AuthBundleProvider pattern from lexigram-auth.

Mount-time phases (controllers, contributors, router) live in the
``lexigram.admin.di.mount`` mixins; this module keeps the provider lifecycle
(register/boot/shutdown/health) and the middleware wiring that must stay
bound to this module's logger.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from lexigram.admin.config import AdminRbacConfig
from lexigram.admin.di.mount import (
    AdminMountContributorsMixin,
    AdminMountControllersMixin,
    AdminMountCoreMixin,
    MountContext,
)
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

_log = get_logger(__name__)

if TYPE_CHECKING:
    from lexigram.admin.config import AdminConfig
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


class AdminProvider(
    AdminMountCoreMixin,
    AdminMountControllersMixin,
    AdminMountContributorsMixin,
    Provider,
):
    """Orchestrates admin sub-providers for the full admin panel.

    Sub-providers are focused helper classes (not Provider subclasses).
    This follows the EventsProvider/AuthBundleProvider pattern.

    Config is accepted only in __init__ and never mutated after construction.
    Sub-providers are instantiated in register() — not in __init__ — so that
    no DI work happens before the container is ready.
    """

    name = "admin"
    priority = ProviderPriority.APPLICATION
    config_key: str | None = None
    # Do NOT declare config_key/config_model — admin config is always set
    # programmatically via AdminModule.configure(), not from YAML auto-injection.

    def __init__(
        self,
        config: AdminConfig | None = None,
        auth_provider: Any | None = None,
        resources: list[type] | None = None,
        controllers: list[type] | None = None,
        extra_providers: list[Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name="admin", priority=ProviderPriority.APPLICATION)
        from lexigram.admin.config import AdminConfig as AdminConfigCls

        self._config = config or AdminConfigCls()
        self._auth_provider = auth_provider
        self._resources = resources or []
        self._controllers = controllers or []
        self._extra_providers: list[Any] = extra_providers or []
        self._kwargs = kwargs

        if (
            self._config.auth.env in {"production", "staging"}
            and not self._config.strict_resource_resolution
        ):
            _log.warning(
                "admin.strict_resource_resolution_disabled_in_production",
                message="strict_resource_resolution=False in production/staging can hide missing admin routes",
            )

        # Sub-providers are populated in register() — empty until then.
        self._sub_providers: list[Any] = []
        self._resolved_resources: dict[str, Any] = {}
        self._nav_item_builder: Any | None = None
        self._admin_resolver: Any | None = None
        self._mount_failures: dict[str, str] = {}
        self._csrf_service: Any | None = None
        # Middleware dependencies resolved in boot(); always assigned before
        # mount_to_app() runs (boot failures fail application startup).
        self._user_store: Any | None = None
        self._session_service: Any | None = None
        self._authorizer: Any | None = None
        self._authorizer_service: Any | None = None

    @property  # type: ignore[misc]
    def config(self) -> AdminConfig:
        """Return current admin config."""
        return self._config

    @classmethod
    def from_config(cls, config: AdminConfig, **context: Any) -> Self:
        """Create provider from typed config."""
        return cls(config=config, **context)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register admin and all sub-providers.

        Sub-providers are instantiated here (not in __init__) so that no DI
        resolution or heavyweight initialisation happens before the container
        lifecycle has started.  No resolution is performed in this method —
        only bindings are registered.
        """
        from lexigram.admin.controllers.dashboard import DashboardController
        from lexigram.admin.controllers.impersonation import ImpersonationController
        from lexigram.admin.controllers.tenancy import TenancyController
        from lexigram.admin.controllers.widgets import WidgetController
        from lexigram.admin.di.sub_providers.auth import AdminAuthSubProvider
        from lexigram.admin.di.sub_providers.contributor import (
            AdminContributorSubProvider,
        )
        from lexigram.admin.di.sub_providers.core import AdminCoreSubProvider
        from lexigram.admin.di.sub_providers.dashboard import AdminDashboardSubProvider
        from lexigram.admin.di.sub_providers.integrations import (
            AdminIntegrationsSubProvider,
        )
        from lexigram.admin.di.sub_providers.realtime import AdminRealtimeSubProvider
        from lexigram.admin.di.sub_providers.resource import AdminResourceSubProvider
        from lexigram.admin.di.sub_providers.tenancy import AdminTenancySubProvider
        from lexigram.admin.di.sub_providers.ui import AdminUISubProvider
        from lexigram.admin.navigation.nav_item_builder import NavItemBuilder

        contributor = AdminContributorSubProvider(
            config=self._config,
            contributors=self._kwargs.get("contributors", []),
        )
        tenancy = AdminTenancySubProvider(config=self._config)
        # Boot order is intentional:
        # 1. Core binds admin primitives used by later providers.
        # 2. Auth binds identity/session services before resources/actions are wired.
        # 3. Resource/UI/realtime bind user-facing admin surfaces.
        # 4. Tenancy decorates data access before dashboard aggregation.
        # 5. Dashboard consumes contributor registry state.
        # 6. Contributor boots last because extension packages may depend on every earlier seat.
        sub_providers: list[Any] = [
            AdminCoreSubProvider(config=self._config, **self._kwargs),
            AdminAuthSubProvider(
                config=self._config, auth_provider=self._auth_provider
            ),
            AdminResourceSubProvider(config=self._config, resources=self._resources),
            AdminUISubProvider(config=self._config),
            AdminRealtimeSubProvider(config=self._config),
            tenancy,
            AdminDashboardSubProvider(
                config=self._config,
                contributor_registry=contributor.registry,
            ),
            contributor,
            AdminIntegrationsSubProvider(config=self._config.integrations),
        ]
        self._sub_providers = sub_providers

        nav_item_builder = NavItemBuilder(config=self._config)
        self._nav_item_builder = nav_item_builder

        container.singleton(AdminProvider, self)
        # Register with string key so web provider can discover without importing admin
        container.singleton("admin_bundle", self)
        # Register NavItemBuilder as a pre-built instance (config is not in container)
        container.singleton(NavItemBuilder, nav_item_builder)
        # Register the resolved RBAC config so @inject consumers read the
        # configured super-admin role, not a fresh default instance.
        container.singleton(AdminRbacConfig, self._config.rbac)
        # Register built-in controllers
        container.singleton(WidgetController, WidgetController)
        container.singleton(TenancyController, TenancyController)
        container.singleton(DashboardController, DashboardController)
        from lexigram.admin.services.impersonation import ImpersonationService

        container.singleton(ImpersonationService, ImpersonationService)
        container.singleton(ImpersonationController, ImpersonationController)
        # Register the RBAC permission inventory (populated at mount time)
        from lexigram.admin.rbac.inventory import PermissionInventoryService

        container.singleton(PermissionInventoryService, PermissionInventoryService)
        # Register controller classes for DI resolution
        for controller_cls in self._controllers:
            try:
                container.singleton(controller_cls, controller_cls)
            except Exception:  # noqa: BLE001 — re-registration is expected; continue loop
                _log.debug(
                    "admin.controller_already_registered",
                    controller=controller_cls.__name__,
                )
        # Register resource classes so the container can inject their service dependencies
        for resource_cls in self._resources:
            try:
                container.singleton(resource_cls, resource_cls)
            except Exception:  # noqa: BLE001 — re-registration is expected; continue loop
                _log.debug(
                    "admin.resource_already_registered", resource=resource_cls.__name__
                )
        for ep in self._extra_providers:
            await ep.register(container)
        for sp in self._sub_providers:
            await sp.register(container)

        # NOTE: TenantConfigProviderProtocol is not registered here — it is
        # constructed directly in mount_to_app() via AdminSettingsDbProvider.

    async def mount_to_app(
        self,
        app: Any,
        container: ContainerResolverProtocol,
    ) -> None:
        """Build and mount the admin panel onto a Starlette application.

        Called by the web provider during route setup, after the Starlette
        app is created and all providers have booted.

        Args:
            app: The Starlette application to mount the admin panel on.
            container: The DI resolver for resolving controller dependencies.
        """
        admin_resolver = self._admin_resolver or container
        ctx = MountContext()
        await self._mount_resources(admin_resolver, ctx)
        await self._mount_settings_service(admin_resolver, ctx)
        await self._mount_controllers(admin_resolver, ctx)
        self._mount_nav_builder(ctx)
        await self._mount_middleware(admin_resolver, ctx)
        self._mount_tenant_scoping(ctx)
        await self._mount_contributors(admin_resolver, ctx)
        await self._mount_integration(container, ctx)
        await self._mount_sse_widgets(container, ctx)
        await self._mount_app_state(app, ctx)
        _log.info("admin.mounted", prefix=self._config.prefix)

    def _mount_nav_builder(self, ctx: MountContext) -> None:
        """Populate the nav item builder with resolved resource instances."""
        from lexigram.admin.navigation.nav_item_builder import NavItemBuilder

        self._resolved_resources = ctx.resources
        nav_builder = self._nav_item_builder
        if nav_builder is None:
            nav_builder = NavItemBuilder(config=self._config)
            self._nav_item_builder = nav_builder
        nav_builder.set_resources(ctx.resources)
        ctx.nav_builder = nav_builder

    async def _mount_middleware(self, admin_resolver: Any, ctx: MountContext) -> None:
        """Resolve and stack admin middleware layers in mount order.

        Args:
            admin_resolver: The DI resolver for middleware dependencies.
            ctx: Mount pipeline state (``middlewares`` populated in place).
        """
        # Resolve SetupMiddleware's dependency: the admin user store.
        # Best-effort — if the store is not registered (e.g. custom auth setups)
        # SetupMiddleware is simply not added and no setup redirect occurs.
        middleware_stack: list[tuple[type, dict[str, Any]]] = []
        try:
            from lexigram.admin.auth.store.protocols import AdminUserStoreProtocol
            from lexigram.admin.middleware.setup import SetupMiddleware

            admin_user_store = await admin_resolver.resolve(
                AdminUserStoreProtocol,
                bypass_visibility=True,
            )
            middleware_stack.append(
                (SetupMiddleware, {"admin_user_store": admin_user_store})
            )
            _log.debug("admin.setup_middleware_wired")
        except Exception as exc:  # noqa: BLE001 — SetupMiddleware is optional
            _log.warning(
                "admin.setup_middleware_skipped",
                reason=str(exc),
            )

        # Wire AdminCsrfMiddleware — REQUIRED. The service is resolved at
        # boot() (see boot()), so a missing binding fails startup, never
        # silently disables CSRF.
        from lexigram.admin.middleware.csrf import AdminCsrfMiddleware

        csrf_service = await self._get_csrf_service(admin_resolver)
        csrf_audit_service = None
        try:
            from lexigram.admin.auth.protocols import (
                AdminAuditLogServiceProtocol,
            )

            csrf_audit_service = await admin_resolver.resolve(
                AdminAuditLogServiceProtocol,
                bypass_visibility=True,
            )
        except Exception as exc:  # noqa: BLE001 — CSRF audit is optional
            _log.warning("admin.csrf_audit_service_unavailable", reason=str(exc))
        middleware_stack.append(
            (
                AdminCsrfMiddleware,
                {
                    "csrf_service": csrf_service,
                    "audit_service": csrf_audit_service,
                },
            )
        )
        _log.debug("admin.csrf_middleware_wired")

        # Wire session-based auth guard — redirects unauthenticated requests to login.
        if self._config.require_auth:
            try:
                from lexigram.admin.middleware.auth_guard import (
                    AdminAuthGuardMiddleware,
                )

                middleware_stack.append((AdminAuthGuardMiddleware, {}))
                _log.debug("admin.auth_guard_middleware_wired")
            except Exception as exc:  # noqa: BLE001 — guard middleware is optional
                # Degrade (non-fatal), but log at error: the operator
                # explicitly required auth and the guard could not be added.
                if self._config.require_auth:
                    _log.error("admin.auth_guard_middleware_skipped", reason=str(exc))
                else:
                    _log.warning("admin.auth_guard_middleware_skipped", reason=str(exc))
        else:
            _log.debug("admin.auth_guard_middleware_skipped_require_auth_unset")

        # Wire auth middleware — loads user from session into request.state.user
        # so that downstream authorization middleware can enforce RBAC.
        # Dependencies resolved in boot(); a missing binding fails startup.
        from lexigram.admin.middleware.auth import AdminAuthMiddleware

        middleware_stack.append(
            (
                AdminAuthMiddleware,
                {
                    "user_store": self._user_store,
                    "session_service": self._session_service,
                    "require_auth": False,
                },
            )
        )
        _log.debug("admin.auth_middleware_wired")

        # Wire request-entry RBAC middleware — checks authorization before
        # dispatching to handlers (AUTH-09, AUTH-18).  Placed after the auth
        # guard so request.state.user is populated. The authorizer is
        # resolved in boot(); a missing binding fails startup.
        from lexigram.admin.middleware.authorization import (
            AdminAuthorizationMiddleware,
        )

        middleware_stack.append(
            (AdminAuthorizationMiddleware, {"authorizer": self._authorizer})
        )
        _log.debug("admin.authorization_middleware_wired")

        # Wire tenant middleware when tenancy is enabled (before auth guard
        # so request.state.tenant_id is available during auth checks).
        if self._config.tenancy.enabled:
            from lexigram.admin.middleware.tenant import AdminTenantMiddleware

            middleware_stack.insert(
                0, (AdminTenantMiddleware, {"config": self._config.tenancy})
            )
            _log.debug("admin.tenant_middleware_wired")

        # Wire AdminErrorMiddleware innermost so it catches exceptions from
        # all other middleware and controllers.  Best-effort — if the
        # middleware fails to resolve, admin runs without custom error pages.
        try:
            from lexigram.admin.middleware.error import AdminErrorMiddleware

            middleware_stack.append(
                (
                    AdminErrorMiddleware,
                    {
                        "debug": self._config.debug,
                        "login_url": f"{self._config.prefix}/login",
                    },
                )
            )
            _log.debug("admin.error_middleware_wired")
        except Exception as exc:  # noqa: BLE001 — error middleware is optional
            _log.warning("admin.error_middleware_skipped", reason=str(exc))

        # Wire HX-Push-Url for body-targeted htmx GETs so client-side
        # navigation (htmx.ajax with target "body") keeps the address bar
        # in sync and htmx history (back/forward) works.
        from lexigram.admin.middleware.nav_push import AdminNavPushMiddleware

        middleware_stack.append((AdminNavPushMiddleware, {}))
        _log.debug("admin.nav_push_middleware_wired")

        ctx.middlewares = middleware_stack

    def _mount_tenant_scoping(self, ctx: MountContext) -> None:
        """Wrap resource data sources with tenant scoping when enabled."""
        if not self._config.tenancy.enabled:
            return
        from lexigram.admin.multitenancy.data_source import TenantScopedDataSource

        tenant_id = self._config.tenancy.default_tenant_id
        tenant_field = self._config.tenancy.tenant_field
        for resource in ctx.resources.values():
            ds = getattr(resource, "data_source", None) or getattr(
                resource, "_data_source", None
            )
            if ds is not None:
                scoped = TenantScopedDataSource(
                    data_source=ds,
                    tenant_id=tenant_id,
                    tenant_field=tenant_field,
                )
                resource.data_source = scoped
        _log.debug("admin.resource_data_sources_tenant_scoped")

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot all sub-providers in order.

        Raises:
            RuntimeError: If the CSRF service cannot be resolved — admin
                must not boot without CSRF enforcement (fail-closed).
        """
        self._admin_resolver = container
        for sp in self._sub_providers:
            await sp.boot(container)

        # CSRF is mandatory. Resolve here, not in mount_to_app(): boot
        # failures propagate through the orchestrator and fail application
        # startup, whereas mount_to_app() exceptions are caught by the web
        # provider's RouteSetup and logged, silently skipping the admin mount.
        from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol

        try:
            self._csrf_service = await container.resolve(
                AdminCsrfServiceProtocol,
                bypass_visibility=True,
            )
        except Exception as exc:  # noqa: BLE001 — re-raised as fatal below
            _log.error(
                "admin.csrf_service_resolution_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise RuntimeError(
                "CSRF service could not be resolved; refusing to boot admin "
                "without CSRF enforcement"
            ) from exc

        # The first-run wizard must be gated: boot refuses to start without
        # a setup token (admin.auth.security.setup_token, legacy env var
        # ADMIN_SETUP_TOKEN, or nested LEX_ADMIN_AUTH__SECURITY__SETUP_TOKEN)
        # unless the operator explicitly opts out with
        # admin.auth.security.setup_token_optin_unsafe=true for local/
        # ephemeral environments only.
        if (
            not self._config.auth.security.setup_token
            and not self._config.auth.security.setup_token_optin_unsafe
        ):
            raise RuntimeError(
                "Refusing to boot admin without a setup token: set "
                "ADMIN_SETUP_TOKEN (or config admin.auth.security.setup_token, "
                "env LEX_ADMIN_AUTH__SECURITY__SETUP_TOKEN), or explicitly opt "
                "out for local/ephemeral environments with "
                "admin.auth.security.setup_token_optin_unsafe=true"
            )

        # AdminAuthMiddleware's dependencies are mandatory — the middleware
        # that actually enforces identity must not be silently dropped by a
        # mount-time resolution failure (RouteSetup swallows mount exception
        # and skips the admin mount entirely). Resolve at boot with the same
        # fail-loud shape as the CSRF block above.
        from lexigram.admin.auth.protocols import AdminSessionServiceProtocol
        from lexigram.admin.auth.store.protocols import AdminUserStoreProtocol

        try:
            self._user_store = await container.resolve(
                AdminUserStoreProtocol,
                bypass_visibility=True,
            )
            self._session_service = await container.resolve(
                AdminSessionServiceProtocol,
                bypass_visibility=True,
            )
        except Exception as exc:  # noqa: BLE001 — re-raised as fatal below
            _log.error(
                "admin.auth_middleware_dependencies_resolution_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise RuntimeError(
                "AdminAuthMiddleware dependencies could not be resolved; "
                "refusing to boot admin without session validation"
            ) from exc

        # AdminAuthorizationMiddleware's authorizer is mandatory — RBAC
        # enforcement must never silently degrade at startup.
        from lexigram.admin.middleware.authorization import (
            RequestAuthorizerProtocol,
        )

        try:
            self._authorizer = await container.resolve(
                RequestAuthorizerProtocol,
                bypass_visibility=True,
            )
        except Exception as exc:  # noqa: BLE001 — re-raised as fatal below
            _log.error(
                "admin.authorization_middleware_dependency_resolution_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise RuntimeError(
                "AdminAuthorizationMiddleware's authorizer could not be "
                "resolved; refusing to boot admin without RBAC enforcement"
            ) from exc

        from lexigram.contracts.auth import AuthorizerProtocol

        try:
            self._authorizer_service = await container.resolve(
                AuthorizerProtocol,
                bypass_visibility=True,
            )
        except Exception as exc:  # noqa: BLE001 — re-raised as fatal below
            _log.error(
                "admin.authorizer_service_resolution_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise RuntimeError(
                "AuthorizerProtocol could not be resolved; refusing to boot "
                "admin without a per-resource permission source for search"
            ) from exc

        # Wire the container resolver into WidgetController so contributor
        # render_widget() implementations can resolve their service dependencies.
        try:
            from lexigram.admin.controllers.widgets import WidgetController

            wc = await container.resolve(WidgetController, bypass_visibility=True)
            wc._resolver = container
        except Exception:
            _log.warning("admin.widget_controller_resolver_wire_failed", exc_info=True)

    async def _get_csrf_service(self, admin_resolver: Any) -> Any:
        """Return the boot-resolved CSRF service, resolving lazily if needed.

        Mount can be invoked directly (tests / factory paths) without a prior
        boot(); in that case resolve here. Failures are never swallowed.

        Raises:
            RuntimeError: If the CSRF service cannot be resolved.
        """
        if self._csrf_service is not None:
            return self._csrf_service
        from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol

        try:
            self._csrf_service = await admin_resolver.resolve(
                AdminCsrfServiceProtocol,
                bypass_visibility=True,
            )
        except Exception as exc:  # noqa: BLE001 — re-raised as fatal below
            raise RuntimeError(
                "CSRF service could not be resolved during admin mount"
            ) from exc
        return self._csrf_service

    async def shutdown(self) -> None:
        """Shut down sub-providers in reverse order."""
        for sp in reversed(self._sub_providers):
            await sp.shutdown()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Aggregate health from all sub-providers."""
        import asyncio

        worst = HealthStatus.HEALTHY
        details: dict[str, Any] = {}
        for sp in self._sub_providers:
            maybe = sp.health_check(timeout)
            result: HealthCheckResult = (
                await maybe if asyncio.iscoroutine(maybe) else maybe
            )
            details[result.component] = result.status.value
            if result.status == HealthStatus.UNHEALTHY:
                worst = HealthStatus.UNHEALTHY
            elif (
                result.status == HealthStatus.DEGRADED
                and worst != HealthStatus.UNHEALTHY
            ):
                worst = HealthStatus.DEGRADED
            elif (
                result.status == HealthStatus.UNKNOWN and worst == HealthStatus.HEALTHY
            ):
                worst = HealthStatus.UNKNOWN

        if self._mount_failures and worst != HealthStatus.UNHEALTHY:
            worst = HealthStatus.DEGRADED
            details["mount_failures"] = dict(self._mount_failures)

        return HealthCheckResult(
            component="admin",
            status=worst,
            message=f"Admin bundle: {worst.value}",
            details=details,
        )


__all__ = ["AdminProvider"]
