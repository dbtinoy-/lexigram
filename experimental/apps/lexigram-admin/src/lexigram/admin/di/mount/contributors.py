"""Mount phases for contributors, routing, SSE and app-state exposure."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.di.mount.context import MountContext

_log = get_logger(__name__)


class AdminMountContributorsMixin:
    """Mount phases that wire contributors, the router and app state."""

    # Host attributes provided by AdminProvider.
    _config: Any
    _resources: list[Any]
    _controllers: list[Any]
    _mount_failures: dict[str, str]
    _authorizer_service: Any
    _get_csrf_service: Any

    async def _mount_contributors(self, resolver: Any, ctx: MountContext) -> None:
        """Discover contributor resources and wire their data sources.

        Contributor discovery is best-effort; failures are recorded in
        ``_mount_failures`` without aborting the mount.

        Args:
            resolver: The DI resolver for contributor resolution.
            ctx: Mount pipeline state (resources/contributors populated).
        """
        from lexigram.admin.contributors.registry import ContributorRegistry
        from lexigram.admin.contributors.resource_collector import ResourceCollector
        from lexigram.admin.dashboard.naming_policy import NamingPolicy

        contributors: list = []
        contributor_registry: Any | None = None
        try:
            contributor_registry = await resolver.resolve(
                ContributorRegistry,
                bypass_visibility=True,
            )
            if contributor_registry is None:
                raise ValueError("Contributor registry unavailable")
            contributors = list(contributor_registry.get_all())
        except Exception as exc:
            _log.warning("admin.contributors_discovery_failed", exc_info=True)
            self._mount_failures["contributor_discovery"] = str(exc)

        ctx.contributors = contributors
        ctx.contributor_registry = contributor_registry

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
                    ctx.resources[name] = await resolver.resolve(
                        resource_cls,
                        bypass_visibility=True,
                    )
                except Exception:  # noqa: BLE001 — fall back to direct
                    try:
                        ctx.resources[name] = resource_cls()
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
            user_permission_inventory: Any = None
            user_resource_cls: Any = None
            try:
                from lexigram.admin.rbac.inventory import PermissionInventoryService
                from lexigram.admin.resources.users import UserResource

                user_permission_inventory = await resolver.resolve(
                    PermissionInventoryService,
                    bypass_visibility=True,
                )
                user_resource_cls = UserResource
            except Exception:  # noqa: BLE001 — best-effort wiring
                _log.debug("admin.user_permission_inventory_unavailable")

            for name, resource in list(ctx.resources.items()):
                if (
                    user_permission_inventory is not None
                    and user_resource_cls is not None
                    and isinstance(resource, user_resource_cls)
                ):
                    try:
                        resource.permission_inventory = user_permission_inventory
                        _log.debug(
                            "admin.user_permission_inventory_wired", resource=name
                        )
                    except Exception:  # noqa: BLE001 — best-effort wiring
                        _log.debug(
                            "admin.user_permission_inventory_wiring_failed",
                            resource=name,
                        )
                dsc = getattr(type(resource), "_data_source_class", None)
                if dsc is not None and hasattr(resource, "set_data_source"):
                    try:
                        ds = await resolver.resolve(dsc, bypass_visibility=True)
                        resource.set_data_source(ds)
                        _log.debug("admin.data_source_wired", resource=name)
                    except Exception:
                        _log.debug("admin.data_source_wiring_failed", resource=name)

                # Wrap data source with search wrappers when the resource
                # has a searchable spec and the search engine is available.
                search_spec = resource.search_spec()
                if search_spec and search_spec.index_name:
                    try:
                        from lexigram.contracts.search import SearchEngineProtocol

                        search_engine = await resolver.resolve(
                            SearchEngineProtocol,
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

        # Give contributors a countable view over the mounted resources.
        # Duck-typed opt-in hook: any contributor exposing
        # ``set_resource_inventory`` receives the inventory (the core
        # contributor uses it for the Resource Overview widget).
        try:
            from lexigram.admin.dashboard.resource_inventory import ResourceInventory

            inventory = ResourceInventory(ctx.resources)
            wired = 0
            for contributor in contributors:
                hook = getattr(contributor, "set_resource_inventory", None)
                if callable(hook):
                    hook(inventory)
                    wired += 1
            if wired:
                _log.info(
                    "admin.resource_inventory_wired",
                    contributors=wired,
                    resources=len(ctx.resources),
                )
        except Exception:  # noqa: BLE001 — inventory wiring is best-effort
            _log.warning("admin.resource_inventory_wiring_failed", exc_info=True)

    async def _mount_integration(self, container: Any, ctx: MountContext) -> None:
        """Build the admin router and integrate contributor routes.

        Args:
            container: The root DI resolver for route integration.
            ctx: Mount pipeline state (``router`` populated).
        """
        from lexigram.admin.core.routing import AdminRouter
        from lexigram.admin.dashboard.naming_policy import NamingPolicy
        from lexigram.admin.dashboard.route_integrator import RouteIntegrator
        from lexigram.admin.rbac.service import PermissionService

        permission_service = None
        try:
            permission_service = await container.resolve(
                PermissionService,
                bypass_visibility=True,
            )
        except Exception:  # noqa: BLE001 — field checks remain opt-in for custom mounts
            _log.warning("admin.permission_service_unavailable_for_forms")

        router = AdminRouter(
            config=self._config,
            resources=ctx.resources,
            controllers=ctx.controllers,
            middleware_stack=ctx.middlewares,
            authorizer=self._authorizer_service,
            permission_service=permission_service,
        )
        ctx.router = router

        try:
            naming = NamingPolicy(mode=self._config.contributor_collision_mode)
            integrator = RouteIntegrator(
                router=router,
                naming_policy=naming,
                route_prefix=self._config.prefix,
                container=container,
            )
            integrator.register(ctx.contributors)
        except Exception as exc:  # noqa: BLE001 — route integration is non-fatal
            _log.warning("admin.contributors_route_integration_failed", exc_info=True)
            self._mount_failures["route_integrator"] = str(exc)

    async def _mount_sse_widgets(self, container: Any, ctx: MountContext) -> None:
        """Register the SSE endpoint for live widget delivery.

        Args:
            container: The root DI resolver for hub/permission services.
            ctx: Mount pipeline state (``router`` read).
        """
        router = ctx.router
        if router is None:
            return
        try:
            from lexigram.admin.dashboard.widget_stream import (
                build_widget_event_stream_handler,
            )
            from lexigram.admin.rbac.service import PermissionService
            from lexigram.admin.realtime.subject_hub import SubjectAdminEventHub
            from lexigram.contracts.web.sse import ReactiveSseBridgeProtocol

            widget_hub: SubjectAdminEventHub = await container.resolve(
                SubjectAdminEventHub
            )
            permission_service: PermissionService = await container.resolve(
                PermissionService
            )
            sse_bridge = await container.resolve(ReactiveSseBridgeProtocol)

            router.add_route(
                "/_sse/widgets",
                "GET",
                build_widget_event_stream_handler(
                    widget_hub, permission_service, sse_bridge=sse_bridge
                ),
                "admin_sse_widgets",
            )
            _log.info("admin.sse_widgets_route_registered", path="/admin/_sse/widgets")
        except Exception as exc:  # noqa: BLE001 — SSE is optional
            _log.warning("admin.sse_widgets_route_skipped", reason=str(exc))

    async def _mount_export_center(self, container: Any, ctx: MountContext) -> None:
        """Register the export center routes (R28 download + R30 pages).

        Mounts, all fixed-path and behind the admin auth guard:

        * ``GET  /exports`` — jobs page (full admin shell).
        * ``POST /exports`` — create + start a background export.
        * ``POST /exports/{job_id}/cancel`` — cancel a running job.
        * ``GET  /exports/{job_id}/download`` — artifact download (R28),
          keyed by the opaque job id with ownership/status checks inside
          the handler.

        Args:
            container: The admin DI resolver holding the ExportService
                singleton registered by AdminExportSubProvider.
            ctx: Mount pipeline state (``router`` and ``resources`` read).
        """
        router = ctx.router
        if router is None:
            return
        try:
            from lexigram.admin.services.export.download import (
                build_export_download_handler,
            )
            from lexigram.admin.services.export.pages import ExportCenter
            from lexigram.admin.services.export.service import ExportService

            export_service: ExportService = await container.resolve(ExportService)

            renderer: Any = None
            try:
                from lexigram.admin.engine.renderer import (
                    AdminRenderer as EngineAdminRenderer,
                )

                renderer = await container.resolve(EngineAdminRenderer)
            except Exception:  # noqa: BLE001 — fall back to a fresh renderer
                from lexigram.admin.engine.renderer import AdminRenderer

                renderer = AdminRenderer()

            permission_service: Any = None
            try:
                from lexigram.admin.rbac.service import PermissionService

                permission_service = await container.resolve(PermissionService)
            except Exception:  # noqa: BLE001 — creation falls back to superuser-only
                permission_service = None

            center = ExportCenter(
                export_service=export_service,
                resources=ctx.resources or {},
                config=self._config,
                renderer=renderer,
                permission_service=permission_service,
            )
            router.add_route("/exports", "GET", center.page, "admin_exports_page")
            router.add_route("/exports", "POST", center.create, "admin_exports_create")
            router.add_route(
                "/exports/jobs",
                "GET",
                center.jobs_fragment,
                "admin_exports_jobs",
            )
            router.add_route(
                "/exports/{job_id}/cancel",
                "POST",
                center.cancel,
                "admin_exports_cancel",
            )
            router.add_route(
                "/exports/{job_id}/download",
                "GET",
                build_export_download_handler(export_service),
                "admin_export_download",
            )
            _log.info(
                "admin.export_center_routes_registered",
                path=f"{self._config.prefix}/exports",
            )

            # Surface the page in the sidebar: any contributor exposing the
            # duck-typed enable_export_center hook gains an "Exports" nav
            # item, gated on the routes above actually registering.
            exports_url = f"{self._config.prefix.rstrip('/')}/exports"
            for contributor in getattr(ctx, "contributors", None) or []:
                hook = getattr(contributor, "enable_export_center", None)
                if callable(hook):
                    try:
                        hook(exports_url)
                        _log.info(
                            "admin.export_center_nav_enabled", url=exports_url
                        )
                    except Exception:  # noqa: BLE001 — nav is best-effort
                        _log.warning(
                            "admin.export_center_nav_hook_failed", exc_info=True
                        )
        except Exception as exc:  # noqa: BLE001 — export center is optional
            _log.warning("admin.export_center_routes_skipped", reason=str(exc))

    async def _mount_csp_reporting(self, ctx: MountContext) -> None:
        """Register CSP violation reporting + wire the Security CSP tab.

        Mounts, fixed-path (docs 30 + 31 — CSP v2 groundwork):

        * ``POST /security/csp-report`` — browser violation report sink
          (CSRF/auth-guard exempt; size-capped; always terse).
        * ``GET  /security/csp-reports`` — superuser-only JSON summary.

        The Security Center controller's CSP tab (``GET /security/csp``,
        R12 controller + doc 31) renders the same store: after the sink
        registers, the store and a settings reader are attached to the
        ``SecurityController`` instance in ``ctx.controllers``
        (best-effort, mirroring how its audit/lockout stores attach in
        ``di/mount/controllers.py``). If attachment fails the tab still
        renders with a "reporting not wired" note.

        Args:
            ctx: Mount pipeline state (``router``, ``controllers`` and
                ``settings_service`` read).
        """
        router = ctx.router
        if router is None:
            return
        try:
            from lexigram.admin.services.security.csp_reports import (
                CspReportEndpoint,
                CspReportStore,
            )

            store = CspReportStore()
            endpoint = CspReportEndpoint(store)
            router.add_route(
                "/security/csp-report",
                "POST",
                endpoint.ingest,
                "admin_csp_report_ingest",
            )
            router.add_route(
                "/security/csp-reports",
                "GET",
                endpoint.list_reports,
                "admin_csp_reports_list",
            )
            _log.info(
                "admin.csp_reporting_registered",
                path=f"{self._config.prefix}/security/csp-report",
            )
        except Exception as exc:  # noqa: BLE001 — reporting is optional
            _log.warning("admin.csp_reporting_skipped", reason=str(exc))
            return

        try:
            settings_store: Any = None
            if ctx.settings_service is not None:
                from lexigram.admin.settings.store import TenantConfigStore

                settings_store = TenantConfigStore(ctx.settings_service)

            from lexigram.admin.controllers.security import SecurityController

            wired = False
            for controller in ctx.controllers or []:
                if isinstance(controller, SecurityController):
                    controller._csp_store = store  # noqa: SLF001 — mount-time wiring, same pattern as _audit_store
                    controller._csp_settings = settings_store  # noqa: SLF001
                    wired = True
            if wired:
                _log.info(
                    "admin.security_csp_tab_wired",
                    path=f"{self._config.prefix}/security/csp",
                )
            else:
                _log.warning(
                    "admin.security_csp_tab_skipped",
                    reason="SecurityController not mounted",
                )
        except Exception as exc:  # noqa: BLE001 — the tab is optional
            _log.warning("admin.security_csp_tab_skipped", reason=str(exc))

    async def _mount_app_state(self, app: Any, ctx: MountContext) -> None:
        """Mount the router and expose nav/registry state on both apps.

        The renderer looks up request.app.state.nav_builder; request.app is
        the *inner* admin sub-app (not the outer Starlette app), so state is
        set on both.

        Args:
            app: The outer Starlette application to mount the panel on.
            ctx: Mount pipeline state (nav/registry state read).
        """
        router = ctx.router
        if router is None:
            return
        admin_app = router.mount(app)
        ctx.admin_app = admin_app

        # Expose nav_builder on app state so AdminRenderer can build the sidebar.
        if hasattr(app, "state"):
            app.state.nav_builder = ctx.nav_builder
        if admin_app is not None and hasattr(admin_app, "state"):
            admin_app.state.nav_builder = ctx.nav_builder

        # Record the configured admin prefix on both apps so URL builders and
        # shell components can resolve it without hard-coding "/admin".
        admin_prefix = getattr(admin_app, "state", None) and getattr(
            admin_app.state, "admin_prefix", None
        )
        if admin_prefix and hasattr(app, "state"):
            app.state.admin_prefix = admin_prefix

        # Build NavigationAssembler contributions and expose on app state.
        assembler_nav_items: list[dict[str, object]] = []
        assembler_groups: dict[str, list[Any]] | None = None
        registry = ctx.contributor_registry
        if registry is not None and ctx.contributors:
            from lexigram.admin.navigation.assembler import (
                NavigationAssembler,
                contributions_to_flat_nav,
            )

            try:
                assembler = NavigationAssembler(
                    contributor_registry=registry,
                    resource_items=[],
                )
                grouped = await assembler.build()
                assembler_groups = grouped
                assembler_nav_items = contributions_to_flat_nav(grouped)
            except Exception:  # noqa: BLE001 — non-fatal
                _log.warning("admin.navigation_assembler_prebuild_failed")
        if hasattr(app, "state"):
            app.state.assembler_nav_items = assembler_nav_items
            app.state.assembler_groups = assembler_groups or {}
        if admin_app is not None and hasattr(admin_app, "state"):
            admin_app.state.assembler_nav_items = assembler_nav_items
            admin_app.state.assembler_groups = assembler_groups or {}

        # Expose the cluster registry on app state so nav resolution and
        # cluster centers resolve the active cluster per request.
        if ctx.cluster_registry is not None:
            if hasattr(app, "state"):
                app.state.cluster_registry = ctx.cluster_registry
            if admin_app is not None and hasattr(admin_app, "state"):
                admin_app.state.cluster_registry = ctx.cluster_registry

        # Expose the configured super-admin role so the shell user menu can
        # gate superadmin-only entries (Security Center — R12).
        super_admin_role = str(
            getattr(self._config.rbac, "super_admin_role", "superadmin") or "superadmin"
        )
        if hasattr(app, "state"):
            app.state.super_admin_role = super_admin_role
        if admin_app is not None and hasattr(admin_app, "state"):
            admin_app.state.super_admin_role = super_admin_role

        # Expose the saved-view service (R13) so ListRenderer — which has no
        # DI access at render time — can read per-user saved views from
        # request.app.state on both the outer and mounted apps.
        if ctx.saved_view_service is not None:
            if hasattr(app, "state"):
                app.state.saved_view_service = ctx.saved_view_service
            if admin_app is not None and hasattr(admin_app, "state"):
                admin_app.state.saved_view_service = ctx.saved_view_service
