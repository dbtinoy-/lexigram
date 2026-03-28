"""Admin bundle provider — orchestrates focused sub-providers.

Follows the AuthBundleProvider pattern from lexigram-auth.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

_log = get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from lexigram.admin.config import AdminConfig
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


class AdminProvider(Provider):
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
        # Register built-in controllers
        container.singleton(WidgetController, WidgetController)
        container.singleton(DashboardController, DashboardController)
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
        from lexigram.admin.core.routing import AdminRouter
        from lexigram.admin.navigation.nav_item_builder import NavItemBuilder

        admin_resolver = self._admin_resolver or container

        # Build resources dict from resource classes {name: instance}
        resources_dict: dict[str, Any] = {}
        for resource_cls in self._resources:
            name = (
                getattr(resource_cls, "name", None)
                or resource_cls.__name__.replace("Resource", "").lower()
            )
            try:
                resources_dict[name] = await admin_resolver.resolve(
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

        # Resolve controller instances from container (best-effort)
        controller_instances: list[Any] = []

        # Create shared settings_service for runtime theme overrides (best-effort)
        admin_settings_service: Any = None
        try:
            from lexigram.admin.services.settings_service import (
                AdminSettingsDbProvider,
                AdminSettingsService,
            )
            from lexigram.contracts.data import DatabaseProviderProtocol

            db_provider = await admin_resolver.resolve(
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
                registry = await admin_resolver.resolve(
                    ConfigRegistry,
                    bypass_visibility=True,
                )
                registry.register_store("db", TenantConfigStore(admin_settings_service))
            except Exception:
                _log.warning("admin.settings_store_registration_failed")
        except Exception:
            try:
                admin_settings_service = AdminSettingsService()
            except Exception:
                pass

        for controller_cls in self._controllers:
            try:
                instance = await admin_resolver.resolve(
                    controller_cls,
                    bypass_visibility=True,
                )
                controller_instances.append(instance)
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
            from lexigram.admin.controllers.widgets import WidgetController

            widget_controller = await admin_resolver.resolve(
                WidgetController,
                bypass_visibility=True,
            )
            controller_instances.append(widget_controller)
            if admin_settings_service is not None and hasattr(
                widget_controller, "_settings_service"
            ):
                widget_controller._settings_service = admin_settings_service
            if audit_service is not None and hasattr(
                widget_controller, "_audit_service"
            ):
                widget_controller._audit_service = audit_service
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

            dashboard_controller = await admin_resolver.resolve(
                DashboardController,
                bypass_visibility=True,
            )
            controller_instances.append(dashboard_controller)
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

            auth_controller = await admin_resolver.resolve(
                AuthController,
                bypass_visibility=True,
            )
            controller_instances.append(auth_controller)
            if admin_settings_service is not None:
                auth_controller._settings_service = admin_settings_service
        except Exception as exc:
            _log.error(
                "admin.auth_controller_resolution_failed",
                error=str(exc),
                strict=self._config.strict_resource_resolution,
            )
            self._mount_failures["controller:AuthController"] = str(exc)
            if self._config.strict_resource_resolution:
                raise

        # Resolve built-in SetupController (first-run wizard)
        try:
            from lexigram.admin.controllers.setup import SetupController

            setup_controller = await admin_resolver.resolve(
                SetupController,
                bypass_visibility=True,
            )
            controller_instances.append(setup_controller)
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

            error_controller = await admin_resolver.resolve(
                ErrorController,
                bypass_visibility=True,
            )
            controller_instances.append(error_controller)
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

            pool_health_controller = await admin_resolver.resolve(
                PoolHealthController,
                bypass_visibility=True,
            )
            controller_instances.append(pool_health_controller)
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
        # in-memory tracker from lexigram-tasks (optional integration —
        # without it the controller is skipped, like other optional seats).
        try:
            from lexigram.admin.controllers.progress import ProgressController

            try:
                progress_controller = await admin_resolver.resolve(
                    ProgressController,
                    bypass_visibility=True,
                )
            except Exception:
                from lexigram.tasks.progress import InMemoryProgressTracker

                progress_controller = ProgressController(
                    tracker=InMemoryProgressTracker()
                )
            controller_instances.append(progress_controller)
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
                AdminCsrfServiceProtocol,
            )
            from lexigram.admin.controllers.settings import SettingsController
            from lexigram.admin.engine.renderer import AdminRenderer
            from lexigram.admin.settings.panel.registry import ConfigRegistry

            csrf_service: AdminCsrfServiceProtocol | None = None
            try:
                csrf_service = await admin_resolver.resolve(
                    AdminCsrfServiceProtocol,
                    bypass_visibility=True,
                )
            except Exception:
                pass

            registry: ConfigRegistry | None = None
            try:
                registry = await admin_resolver.resolve(
                    ConfigRegistry,
                    bypass_visibility=True,
                )
            except Exception:
                pass

            audit_service: AdminAuditLogServiceProtocol | None = None
            try:
                audit_service = await admin_resolver.resolve(
                    AdminAuditLogServiceProtocol,
                    bypass_visibility=True,
                )
            except Exception:
                pass

            renderer = await admin_resolver.resolve(
                AdminRenderer,
                bypass_visibility=True,
            )
            settings_controller = SettingsController(
                renderer=renderer,
                settings_service=admin_settings_service,
                csrf_service=csrf_service,
                audit_service=audit_service,
                registry=registry,
            )
            controller_instances.append(settings_controller)
        except Exception as exc:
            _log.warning(
                "admin.settings_controller_skipped",
                error=str(exc),
            )

        # Populate NavItemBuilder with resolved resource instances
        self._resolved_resources = resources_dict
        nav_builder = self._nav_item_builder
        if nav_builder is None:
            nav_builder = NavItemBuilder(config=self._config)
            self._nav_item_builder = nav_builder
        nav_builder.set_resources(resources_dict)

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

        # Wire AdminCsrfMiddleware when the CSRF service is available.
        try:
            from lexigram.admin.auth.protocols import (
                AdminAuditLogServiceProtocol,
                AdminCsrfServiceProtocol,
            )
            from lexigram.admin.middleware.csrf import AdminCsrfMiddleware

            csrf_service = await admin_resolver.resolve(
                AdminCsrfServiceProtocol,
                bypass_visibility=True,
            )
            csrf_audit_service = None
            try:
                csrf_audit_service = await admin_resolver.resolve(
                    AdminAuditLogServiceProtocol,
                    bypass_visibility=True,
                )
            except Exception:  # noqa: BLE001 — CSRF audit is optional
                pass
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
        except Exception as exc:  # noqa: BLE001 — CSRF middleware is optional
            _log.warning("admin.csrf_middleware_skipped", reason=str(exc))

        # Wire session-based auth guard — redirects unauthenticated requests to login.
        if self._config.require_auth:
            try:
                from lexigram.admin.middleware.auth_guard import (
                    AdminAuthGuardMiddleware,
                )

                middleware_stack.append((AdminAuthGuardMiddleware, {}))
                _log.debug("admin.auth_guard_middleware_wired")
            except Exception as exc:  # noqa: BLE001 — guard middleware is optional
                _log.warning("admin.auth_guard_middleware_skipped", reason=str(exc))
        else:
            _log.debug("admin.auth_guard_middleware_skipped_require_auth_unset")

        # Wire auth middleware — loads user from session into request.state.user
        # so that downstream authorization middleware can enforce RBAC.
        try:
            from lexigram.admin.auth.protocols import AdminSessionServiceProtocol
            from lexigram.admin.auth.store.protocols import AdminUserStoreProtocol
            from lexigram.admin.middleware.auth import AdminAuthMiddleware

            user_store = await admin_resolver.resolve(
                AdminUserStoreProtocol,
                bypass_visibility=True,
            )
            session_service = await admin_resolver.resolve(
                AdminSessionServiceProtocol,
                bypass_visibility=True,
            )
            middleware_stack.append(
                (
                    AdminAuthMiddleware,
                    {
                        "user_store": user_store,
                        "session_service": session_service,
                        "require_auth": False,
                    },
                )
            )
            _log.debug("admin.auth_middleware_wired")
        except Exception as exc:  # noqa: BLE001 — auth middleware is optional
            _log.warning("admin.auth_middleware_skipped", reason=str(exc))

        # Wire request-entry RBAC middleware — checks authorization before
        # dispatching to handlers (AUTH-09, AUTH-18).  Placed after the auth
        # guard so request.state.user is populated.
        try:
            from lexigram.admin.middleware.authorization import (
                AdminAuthorizationMiddleware,
            )
            from lexigram.contracts.admin.authorizer import (
                AdminAuthorizerProtocol,
            )

            authorizer = await admin_resolver.resolve(
                AdminAuthorizerProtocol,
                bypass_visibility=True,
            )
            middleware_stack.append(
                (AdminAuthorizationMiddleware, {"authorizer": authorizer})
            )
            _log.debug("admin.authorization_middleware_wired")
        except Exception as exc:  # noqa: BLE001 — authorization middleware is optional
            _log.warning("admin.authorization_middleware_skipped", reason=str(exc))

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

        # Wrap resource data sources with tenant scoping when enabled
        if self._config.tenancy.enabled:
            from lexigram.admin.multitenancy.data_source import TenantScopedDataSource

            tenant_id = self._config.tenancy.default_tenant_id
            tenant_field = self._config.tenancy.tenant_field
            for resource in resources_dict.values():
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

        from lexigram.admin.contributors.registry import ContributorRegistry
        from lexigram.admin.contributors.resource_collector import ResourceCollector
        from lexigram.admin.dashboard.naming_policy import NamingPolicy
        from lexigram.admin.dashboard.route_integrator import RouteIntegrator

        contributors: list = []
        try:
            registry = await admin_resolver.resolve(
                ContributorRegistry,
                bypass_visibility=True,
            )
            contributors = list(registry.get_all())
        except Exception as exc:
            _log.warning("admin.contributors_discovery_failed", exc_info=True)
            self._mount_failures["contributor_discovery"] = str(exc)

        try:
            naming = NamingPolicy(mode=self._config.contributor_collision_mode)
            collector = ResourceCollector(naming_policy=naming)
            contributor_resources = collector.collect(contributors)
            for resource_cls in contributor_resources:
                name = (
                    getattr(resource_cls, "name", None)
                    or resource_cls.__name__.replace("Resource", "").lower()
                )
                try:
                    resources_dict[name] = await admin_resolver.resolve(
                        resource_cls,
                        bypass_visibility=True,
                    )
                except Exception:  # noqa: BLE001 — fall back to direct
                    try:
                        resources_dict[name] = resource_cls()
                    except Exception as inner:  # noqa: BLE001 — skip, log warning
                        _log.warning(
                            "admin.contributor_resource_resolution_failed",
                            resource=resource_cls.__name__,
                            contributor=name,
                            error=str(inner),
                        )
                        self._mount_failures[f"contributor_resource:{name}"] = str(
                            inner
                        )

            # Wire data sources to resolved resources that declare _data_source_class
            for name, resource in list(resources_dict.items()):
                dsc = getattr(type(resource), "_data_source_class", None)
                if dsc is not None and hasattr(resource, "set_data_source"):
                    try:
                        ds = await admin_resolver.resolve(dsc, bypass_visibility=True)
                        resource.set_data_source(ds)
                        _log.debug("admin.data_source_wired", resource=name)
                    except Exception:
                        _log.debug("admin.data_source_wiring_failed", resource=name)

                # Wrap data source with search wrappers when the resource
                # has a searchable spec and the search engine is available.
                search_spec = resource.search_spec()
                if search_spec and search_spec.index_name:
                    try:
                        from lexigram.search.engine import SearchEngine

                        search_engine = await admin_resolver.resolve(
                            SearchEngine,
                            bypass_visibility=True,
                        )

                        from lexigram.admin.integrations.search_query import (
                            SearchQueryDataSourceWrapper,
                        )
                        from lexigram.admin.integrations.search_sync import (
                            SearchSyncDataSourceWrapper,
                        )

                        fallback_to_like = getattr(
                            self._config.integrations.search,
                            "fallback_to_like",
                            True,
                        )
                        query_wrapped = SearchQueryDataSourceWrapper(
                            ds,
                            search_engine,
                            search_spec.index_name,
                            fallback_to_like=fallback_to_like,
                        )
                        wrapped = SearchSyncDataSourceWrapper(
                            query_wrapped, search_engine, search_spec
                        )
                        resource.set_data_source(wrapped)
                        _log.debug("admin.search_wired", resource=name)
                    except Exception:
                        _log.debug("admin.search_wiring_failed", resource=name)

        except Exception:  # noqa: BLE001 — resource collection is non-fatal
            _log.warning("admin.contributors_resource_collection_failed", exc_info=True)

        router = AdminRouter(
            config=self._config,
            resources=resources_dict,
            controllers=controller_instances,
            middleware_stack=middleware_stack,
        )

        try:
            naming = NamingPolicy(mode=self._config.contributor_collision_mode)
            integrator = RouteIntegrator(
                router=router,
                naming_policy=naming,
                route_prefix=self._config.prefix,
                container=container,
            )
            integrator.register(contributors)
        except Exception as exc:  # noqa: BLE001 — route integration is non-fatal
            _log.warning("admin.contributors_route_integration_failed", exc_info=True)
            self._mount_failures["route_integrator"] = str(exc)

        # Register SSE endpoint for real-time notification streaming
        try:
            from lexigram.admin.realtime.sse import AdminEventHub, AdminEventsHandler  # noqa: I001
            from lexigram.serialization import dumps_str
            from starlette.responses import StreamingResponse

            hub: AdminEventHub = await container.resolve(AdminEventHub)

            async def sse_event_stream(request: Any) -> StreamingResponse:
                handler = AdminEventsHandler(hub)

                async def event_generator() -> AsyncGenerator[str, None]:
                    try:
                        async for event_dict in handler.stream(request):
                            data_str = dumps_str(event_dict.get("data", {}))
                            event_name = event_dict.get("event", "message")
                            event_id = event_dict.get("id")
                            yield f"event: {event_name}\ndata: {data_str}\n"
                            if event_id:
                                yield f"id: {event_id}\n"
                            yield "\n"
                    except GeneratorExit:
                        pass
                    except RuntimeError:
                        pass

                return StreamingResponse(
                    event_generator(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                    },
                )

            router.add_route(
                "/_sse/events",
                "GET",
                sse_event_stream,
                "admin_sse",
            )
            _log.info("admin.sse_route_registered", path="/admin/_sse/events")
        except Exception as exc:  # noqa: BLE001 — SSE is optional
            _log.warning("admin.sse_route_skipped", reason=str(exc))

        admin_app = router.mount(app)

        # Expose nav_builder on app state so AdminRenderer can build the sidebar.
        # The renderer looks up request.app.state.nav_builder; request.app is the
        # *inner* admin sub-app (not the outer Starlette app), so we set state on both.
        if hasattr(app, "state"):
            app.state.nav_builder = nav_builder
        if admin_app is not None and hasattr(admin_app, "state"):
            admin_app.state.nav_builder = nav_builder

        # Build NavigationAssembler contributions and expose on app state.
        assembler_nav_items: list[dict[str, object]] = []
        _registry = locals().get("registry")
        if _registry and contributors:
            from lexigram.admin.navigation.assembler import (
                NavigationAssembler,
                contributions_to_flat_nav,
            )

            try:
                assembler = NavigationAssembler(
                    contributor_registry=_registry,
                    resource_items=[],
                )
                grouped = await assembler.build()
                assembler_nav_items = contributions_to_flat_nav(grouped)
            except Exception:  # noqa: BLE001 — non-fatal
                _log.warning("admin.navigation_assembler_prebuild_failed")
        if hasattr(app, "state"):
            app.state.assembler_nav_items = assembler_nav_items
        if admin_app is not None and hasattr(admin_app, "state"):
            admin_app.state.assembler_nav_items = assembler_nav_items

        _log.info("admin.mounted", prefix=self._config.prefix)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot all sub-providers in order."""
        self._admin_resolver = container
        for sp in self._sub_providers:
            await sp.boot(container)
        # Wire the container resolver into WidgetController so contributor
        # render_widget() implementations can resolve their service dependencies.
        try:
            from lexigram.admin.controllers.widgets import WidgetController

            wc = await container.resolve(WidgetController, bypass_visibility=True)
            wc._resolver = container
        except Exception:
            _log.warning("admin.widget_controller_resolver_wire_failed", exc_info=True)

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
