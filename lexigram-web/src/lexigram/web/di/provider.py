"""WebProvider - Main web provider with pass-through architecture"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from starlette.applications import Starlette
from starlette.responses import JSONResponse

from lexigram.contracts.core import (
    HealthCheckResult,
    HealthStatus,
    HookRegistryProtocol,
    ProviderPriority,
)
from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.exceptions.config import ConfigurationError
from lexigram.contracts.web import WebProviderProtocol
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.web.config import WebConfig, WebProviderConfig
from lexigram.web.di.middleware_setup import MiddlewareSetup
from lexigram.web.di.route_setup import RouteSetup
from lexigram.web.docs.generator import OpenAPIGenerator
from lexigram.web.integrations.auth import AuthIntegration
from lexigram.web.integrations.cache import CacheIntegration
from lexigram.web.integrations.graphql import GraphQLIntegration
from lexigram.web.integrations.rate_limit import RateLimitIntegration
from lexigram.web.integrations.setup import lifespan
from lexigram.web.integrations.sql import SQLIntegration
from lexigram.web.middleware.manager import WebMiddlewareManager
from lexigram.web.routing.controllers import Controller
from lexigram.web.routing.manager import WebRouterManager
from lexigram.web.routing.router import Router

# Optional external server - imported lazily to avoid dependency issues
# Only needed when run_server() is called

logger = get_logger(__name__)


class WebProvider(Provider):
    """Web provider with native Starlette integration and pass-through architecture.

    **Recommended usage** — let the orchestrator inject configuration via
    ``application.yaml`` (uses ``config_key = "web"`` and ``config_model = WebConfig``)::

        app.add_provider(WebProvider())

    **Config-first factory** — construct from an explicit ``WebConfig``::

        from lexigram.web import WebProvider, WebConfig

        app.add_provider(WebProvider.from_config(WebConfig(debug=True, ...)))

    **Advanced** — pass individual components explicitly (e.g. for tests)::

        app.add_provider(WebProvider(
            controllers=[UsersController],
            middleware=[AuthMiddleware],
            web_config=WebConfig(debug=True),
        ))

    Note: The multi-parameter constructor is intended for advanced and test
    scenarios.  For typical applications, prefer the no-arg or ``from_config()``
    form so that configuration is driven by ``application.yaml``.
    """

    name = "web"
    priority = ProviderPriority.PRESENTATION

    def __init__(
        self,
        middleware: list[Any] | None = None,
        exception_handlers: dict[Any, Any] | None = None,
        controllers: list[type[Controller]] | None = None,
        web_config: WebConfig | None = None,
        provider_config: WebProviderConfig | None = None,
        debug_routes_auth: Callable[..., Any] | None = None,
    ) -> None:
        super().__init__()
        self.middleware = middleware or []
        self.exception_handlers = exception_handlers or {}
        self.controllers = controllers or []

        self.web_config = web_config or WebConfig()
        self._explicit_web_config = web_config is not None
        self.provider_config = provider_config or WebProviderConfig()

        self.starlette: Starlette | None = None
        self._hook_registry: HookRegistryProtocol | None = None

        # Managers
        self.middleware_manager = WebMiddlewareManager(self)
        self.router_manager: WebRouterManager = WebRouterManager(self)

        # Internal state for routing
        self.router: Router | None = None  # Lazy loaded if needed
        self.openapi_generator: OpenAPIGenerator | None = None

        # Route conflict behavior (default: do not raise on duplicate routes)
        # Tests expect duplicate registrations to emit warnings unless explicitly configured
        self.fail_on_route_conflict = getattr(
            self.provider_config,
            "fail_on_route_conflict",
            False,
        )

        # Debug routes config
        self.debug_routes_auth: Callable[..., Any] | None = debug_routes_auth
        self._debug_redis_client: Any | None = None

        # Extra services to register in DI (used by quickstart auto-injection)
        self._extra_injectable_services: list[tuple[type, Any]] = []

        # Web contributor registry for entry-point-based controller/middleware discovery
        from lexigram.web.contributors import WebContributorRegistry

        self._contributor_registry = WebContributorRegistry()

    @property
    def contributor_registry(self) -> Any:
        """Expose contributor registry for route setup access."""
        return self._contributor_registry

    @classmethod
    def from_config(cls, config: WebConfig, **context: Any) -> WebProvider:
        """Create a WebProvider from config.

        Context kwargs may include middleware, controllers, exception_handlers.
        """
        return cls(
            web_config=config,
            middleware=context.get("middleware"),
            controllers=context.get("controllers"),
            exception_handlers=context.get("exception_handlers"),
        )

    @classmethod
    def auto_discover(
        cls,
        *packages: str,
        web_config: WebConfig | None = None,
        **kwargs: Any,
    ) -> WebProvider:
        """Create a WebProvider with controllers auto-discovered from packages.

        Scans each package recursively for
        :class:`~lexigram.web.routing.controllers.Controller` subclasses and
        registers them automatically.

        Args:
            *packages: Dotted Python package paths to scan for controllers,
                e.g. ``"my_app.api.controllers"``.
            web_config: Optional web configuration. Falls back to defaults.
            **kwargs: Extra kwargs forwarded to :class:`WebProvider.__init__`.

        Returns:
            A configured :class:`WebProvider` instance.

        Example::

            app.add_provider(WebProvider.auto_discover("my_app.api.controllers"))
        """
        from lexigram.web.routing.discovery import discover_controllers

        controllers = discover_controllers(list(packages))
        return cls(controllers=controllers, web_config=web_config, **kwargs)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register web services in DI container"""

        # GuardProtocol: debug routes with no protection would expose the entire DI graph.
        # Require at least one protection mechanism: a token or an auth callback.
        if (
            self.web_config.debug_routes
            and not self.web_config.debug_routes_token
            and self.debug_routes_auth is None
        ):
            raise ConfigurationError(
                "debug_routes=True requires either debug_routes_token (in WebConfig) "
                "or a debug_routes_auth callback (in WebProvider). "
                "Set one to protect the debug endpoint."
            )

        container.singleton(WebProvider, self)
        container.singleton(WebProviderProtocol, self)

        from lexigram.primitives.context import Context, create_default_context

        container.singleton(Context, create_default_context())

        from lexigram.web.security.config import (
            CORSConfig,
            CrossOriginConfig,
            CSPConfig,
            CSRFConfig,
            HSTSConfig,
            SecurityConfig,
            SecurityHeadersConfig,
        )
        from lexigram.web.security.cors.middleware import CORSMiddlewareFactory
        from lexigram.web.security.csrf.protection import CSRFProtection

        container.singleton(SecurityConfig, self.web_config.security)
        container.singleton(CORSConfig, self.web_config.cors)
        container.singleton(CSRFConfig, self.web_config.security.csrf)
        container.singleton(SecurityHeadersConfig, self.web_config.security.headers)
        container.singleton(HSTSConfig, self.web_config.security.hsts)
        container.singleton(CSPConfig, self.web_config.security.csp)
        container.singleton(CrossOriginConfig, self.web_config.security.cross_origin)
        container.singleton(
            CORSMiddlewareFactory,
            CORSMiddlewareFactory(config=self.web_config.cors),
        )
        container.singleton(
            CSRFProtection,
            CSRFProtection(config=self.web_config.security.csrf),
        )

        # Register the global route registry so DI resolution returns the same
        # instance that @route decorators populated at import time.
        from lexigram.web.routing.registry import RouteRegistry, route_registry

        container.singleton(RouteRegistry, route_registry)

        # Register the global controller registry so DI resolution returns the same
        # instance that @controller decorators populated at import time.
        from lexigram.web.routing.controller_registry import (
            ControllerRegistry,
            controller_registry,
        )

        container.singleton(ControllerRegistry, controller_registry)

        # Register FilterPipeline and InterceptorPipeline as container singletons so
        # they can be injected rather than accessed via module-level globals.
        from lexigram.web.filters.pipeline import FilterPipeline, filter_pipeline

        container.singleton(FilterPipeline, filter_pipeline)

        from lexigram.web.interceptors.pipeline import InterceptorPipeline

        container.singleton(InterceptorPipeline, InterceptorPipeline())

        # Register Router for dependency injection (pre-instantiated so the DI
        # framework does not inject the FilterPipeline singleton into it and
        # accidentally pollute the global filter pipeline with Router-local filters).
        container.singleton(Router, Router())

        # Register ResponseFactoryProtocol
        from lexigram.contracts.web import ResponseFactoryProtocol
        from lexigram.web.responses import StarletteResponseAdapter

        container.singleton(ResponseFactoryProtocol, StarletteResponseAdapter)

        # Register ResponseSerializer so the router can resolve it per-request
        # without hitting an UnresolvableDependencyError.
        from lexigram.web.serialization.serializers import ResponseSerializer

        container.singleton(ResponseSerializer, ResponseSerializer())

        # Register BackgroundTaskRunnerProtocol — per-resolution (transient) so each
        # caller gets an independent task accumulator bound to its own Starlette context.
        # Background tasks are in-process only. Durable job submission uses explicit
        # lexigram-tasks job APIs, not this web background-runner interface.
        from lexigram.contracts.web.protocols import BackgroundTaskRunnerProtocol
        from lexigram.web.background.tasks import StarletteBackgroundTaskRunner

        container.transient(
            cast("Any", BackgroundTaskRunnerProtocol),
            cast("Any", StarletteBackgroundTaskRunner),
        )

        # Note: ObjectMapperProtocol is NOT auto-registered here because
        # lexigram-mapping is a separate extension package. Register it
        # explicitly via MappingModule.configure() in your application setup.

        # Register admin widget renderer and handlers (transient for scope safety)
        from lexigram.web.admin.contributor import WebAdminContributor
        from lexigram.web.admin.handlers.active_connections import (
            ActiveConnectionsWidgetHandler,
        )
        from lexigram.web.admin.handlers.request_rate import (
            RequestRateWidgetHandler,
        )
        from lexigram.web.admin.handlers.server_status import (
            ServerStatusWidgetHandler,
        )
        from lexigram.web.admin.renderer import PackageWidgetRenderer

        container.singleton(PackageWidgetRenderer, PackageWidgetRenderer)
        container.transient(ServerStatusWidgetHandler, ServerStatusWidgetHandler)
        container.transient(
            ActiveConnectionsWidgetHandler,
            ActiveConnectionsWidgetHandler,
        )
        container.transient(RequestRateWidgetHandler, RequestRateWidgetHandler)
        container.singleton(WebAdminContributor, WebAdminContributor)

        # Register the web contributor registry as a singleton
        from lexigram.web.contributors import WebContributorRegistry
        from lexigram.web.contributors import discovery as contributor_discovery

        container.singleton(WebContributorRegistry, self._contributor_registry)

        # Discover and merge web contributors from entry-points
        for contributor in contributor_discovery.load_web_contributors():
            self._contributor_registry.register(contributor)

            # Merge contributed middleware (avoid duplicates)
            for middleware_cls in contributor.get_middleware():
                if middleware_cls not in self.middleware:
                    self.middleware.append(middleware_cls)

            # Merge contributed controllers (avoid duplicates and
            # subclass-takes-precedence — if a subclass of the contributed
            # controller is already registered, skip the contributed one).
            for controller_cls in contributor.get_controllers():
                if controller_cls not in self.controllers:
                    # Skip if a registered controller is a subclass — the
                    # user-supplied override should take precedence over the
                    # framework's own controller.
                    if isinstance(controller_cls, type) and any(
                        isinstance(ec, type)
                        and ec is not controller_cls
                        and issubclass(ec, controller_cls)
                        for ec in self.controllers
                    ):
                        continue
                    self.controllers.append(controller_cls)

        # Register controllers as singletons if they are classes
        for controller_cls in self.controllers:
            if isinstance(controller_cls, type):
                container.singleton(controller_cls, controller_cls)

        # Expose the active middleware pipeline to admin pages and tooling.
        # The registry mirrors exactly what the app runs: the always-present
        # DIScopeMiddleware plus contributed and user-supplied middleware.
        from lexigram.web.middleware.base import MiddlewareRegistry
        from lexigram.web.middleware.di_scope import DIScopeMiddleware
        from lexigram.web.middleware.registry import (
            MiddlewareAdapterRegistry,
        )

        middleware_registry = MiddlewareRegistry()
        middleware_registry.register_middleware(DIScopeMiddleware)
        for middleware_cls in self.middleware:
            cls = (
                middleware_cls
                if isinstance(middleware_cls, type)
                else type(middleware_cls)
            )
            middleware_registry.register_middleware(cls)
        container.singleton(MiddlewareRegistry, middleware_registry)
        container.singleton(
            MiddlewareAdapterRegistry,
            MiddlewareAdapterRegistry(),
        )

        # Auto-register user classes decorated with @singleton / @injectable.
        # Scan loaded non-framework modules so script-mode apps work without
        # manually calling container.singleton() for each service.
        self._register_injectable_services(container)

    def _register_injectable_services(
        self, container: ContainerRegistrarProtocol
    ) -> None:
        """Register services explicitly provided via ``_extra_injectable_services``.

        This replaces the former sys.modules scanning with explicit service lists,
        making DI registration deterministic and order-independent. Services must be
        explicitly provided to the provider at construction time.
        """
        from lexigram.contracts.core.scopes import ServiceScope

        def _register_one(cls: type, scope: Any) -> None:
            if container.has(cls):
                return
            if scope == ServiceScope.SINGLETON:
                container.singleton(cls, cls)
            elif scope == ServiceScope.SCOPED:
                container.scoped(cls, cls)
            else:
                container.transient(cls, cls)
            logger.debug("auto_registered_injectable", cls=cls.__name__, scope=scope)

        # Register only explicitly provided services
        for cls, scope in self._extra_injectable_services:
            _register_one(cls, scope)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Initialize the web layer in five ordered phases.

        Phase 1 — OpenAPI generator
            Instantiates :class:`~lexigram.web.routing.OpenAPIGenerator` with
            title and version from :attr:`web_config`.

        Phase 2 — Starlette application
            Builds the native ASGI ``Starlette`` instance.  The middleware stack
            is composed **once** here; it is never rebuilt at request time.
            Container and config are attached to ``app.state``.

        Phase 3 — Middleware pipeline
            Iterates registered :class:`~lexigram.web.middleware.AbstractMiddleware`
            subclasses and wraps the Starlette app.  Order follows the provider
            registration order (outermost-first).

        Phase 4 — Integration setup
            Wires optional first-class integrations: authentication, rate
            limiting, GraphQL gateway.  Each integration is only activated when
            its config key is present in the resolved container.

        Phase 5 — Route registration
            Discovers annotated controller methods and mounts them on the
            Starlette router.  Route-level dependencies (guards, interceptors,
            serializers) are resolved here.
        """
        logger.info("Booting WebProvider")

        # Create FilterPipeline with debug mode based on environment
        from lexigram.logging.debug import is_debug_mode
        from lexigram.web.filters.pipeline import FilterPipeline

        _debug_mode = is_debug_mode() or self.web_config.server.debug
        self.router = Router(filter_pipeline=FilterPipeline(debug=_debug_mode))
        self._hook_registry = await container.resolve_optional(HookRegistryProtocol)

        # 1. Initialize OpenAPI generator
        self.openapi_generator = OpenAPIGenerator(
            title=str(getattr(self.web_config, "openapi_title", "Lexigram API")),
            version=str(getattr(self.web_config, "openapi_version", "0.1.0")),
        )

        # 2. Initialize native Starlette app
        self.starlette = self._init_starlette(container)
        self.starlette.state.hook_registry = self._hook_registry

        # 3. Setup Middlewares
        await self._setup_middleware(self.starlette, container)

        # 4. Setup Integrations (Auth, Rate Limit, GraphQL)
        await self._setup_integrations(self.starlette, container)

        # 5. Register Routes
        await self._setup_routes(self.starlette, container)

        # 6. Boot admin contributor
        from lexigram.web.admin.contributor import WebAdminContributor

        contributor = await container.resolve_optional(WebAdminContributor)
        if contributor is not None:
            await contributor.on_admin_boot(container)

        logger.info("Web application startup complete")

    def _init_starlette(self, container: ContainerResolverProtocol) -> Starlette:
        """Initialize the Starlette application instance."""
        from lexigram.web.integrations.starlette import build_starlette_app

        # Build initial middleware stack
        native_middleware = self.middleware_manager.build_native_stack(container)

        return build_starlette_app(
            middleware=native_middleware,
            exception_handlers=self.exception_handlers,
            lifespan=lifespan,
            container=container,
        )

    async def _setup_middleware(
        self, app: Starlette, container: ContainerResolverProtocol
    ) -> None:
        """Configure application-level middlewares via :class:`MiddlewareSetup`."""
        setup = MiddlewareSetup(self.web_config, hooks=self._hook_registry)
        await setup.configure(app, container)

    async def _setup_integrations(
        self, app: Starlette, container: ContainerResolverProtocol
    ) -> None:
        """Configure external integrations and complex subsystems."""
        # 1. Rate Limiting
        await RateLimitIntegration.configure(
            app, cast("Any", container), self.web_config
        )

        # 2. Authentication
        if self.web_config.enable_auth:
            await AuthIntegration.configure(
                app, cast("Any", container), self.web_config
            )

        # 3. GraphQL - WebSocket routes (HTTP handled by web contributor)
        await GraphQLIntegration.configure(app, container)

        # 4. SQL Integration - attach db_pool to app.state for lifespan cleanup
        await SQLIntegration.configure(app, container)

        # 5. Cache Integration - attach redis_client to app.state for lifespan cleanup
        await CacheIntegration.configure(app, container)

        # 6. Default exception filter (handles DomainError, HTTPError, etc.)
        from lexigram.logging.debug import is_debug_mode
        from lexigram.web.filters import DefaultExceptionFilter

        _debug_on = is_debug_mode() or self.web_config.server.debug
        default_filter = DefaultExceptionFilter(debug=_debug_on)
        if not hasattr(app.state, "exception_filters"):
            app.state.exception_filters = []
        app.state.exception_filters.append(default_filter)

        # 5. Global Exception Handlers
        from lexigram.web.exceptions import DependencyResolutionError

        app.add_exception_handler(
            DependencyResolutionError,
            self._dependency_resolution_handler,
        )

    async def _setup_routes(
        self, app: Starlette, container: ContainerResolverProtocol
    ) -> None:
        """Register application routes and mounts via :class:`RouteSetup`."""
        setup = RouteSetup(self.web_config, self.provider_config, self.router_manager)
        await setup.configure(app, container, provider_context=self)

    # -- Handlers ----------------------------------------------------------

    def _dependency_resolution_handler(
        self, request: Any, exc: Exception
    ) -> JSONResponse:
        return JSONResponse(
            {
                "error": "dependency_resolution_error",
                "message": str(exc),
                "details": getattr(exc, "details", {}),
            },
            status_code=500,
        )

    async def shutdown(self) -> None:
        """Cleanup resources created by this provider."""
        logger.info("Shutting down WebProvider...")
        self._debug_redis_client = None
        self._hook_registry = None
        self.starlette = None
        logger.info("WebProvider shutdown complete")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check web provider health."""
        return HealthCheckResult(
            component="web",
            status=HealthStatus.HEALTHY
            if self.starlette is not None
            else HealthStatus.UNHEALTHY,
            details={
                "starlette_initialized": self.starlette is not None,
            },
        )

    def run_server(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        **kwargs: Any,
    ) -> None:
        """Run the web application using Granian.

        See :func:`lexigram.web.server.runner.run_server` for implementation.
        """
        from lexigram.web.server.runner import run_server as _run_server

        if self.starlette is None:
            raise RuntimeError(
                "Starlette app not initialized. Call boot() on the provider first."
            )

        _run_server(self.starlette, host=host, port=port, **kwargs)


__all__ = ["WebProvider"]
