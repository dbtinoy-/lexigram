"""Registration-group sections for :class:`~lexigram.web.di.provider.WebProvider`.

Each function registers one cohesive group of services into the DI
container. They are invoked by ``WebProvider.register()`` at fixed,
ordered positions so the effective registration sequence is identical to
the pre-extraction monolithic implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from lexigram.contracts.web import WebProviderProtocol
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerRegistrarProtocol
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.routing.controllers import Controller

logger = get_logger(__name__)


def register_transport_services(
    provider: WebProvider,
    container: ContainerRegistrarProtocol,
) -> None:
    """Register the web provider instance and transport-level singletons."""
    from lexigram.web.di.provider import WebProvider

    container.singleton(WebProvider, provider)
    container.singleton(WebProviderProtocol, provider)

    from lexigram.contracts.web.sse import ReactiveSseBridgeProtocol
    from lexigram.web.transport.reactive import sse_from_stream

    container.singleton(ReactiveSseBridgeProtocol, sse_from_stream)

    from lexigram.primitives.context import Context, create_default_context

    container.singleton(Context, create_default_context())


def register_security_services(
    provider: WebProvider,
    container: ContainerRegistrarProtocol,
) -> None:
    """Register security configuration objects and the CORS middleware factory."""
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

    container.singleton(SecurityConfig, provider.web_config.security)
    container.singleton(CORSConfig, provider.web_config.cors)
    container.singleton(CSRFConfig, provider.web_config.security.csrf)
    container.singleton(SecurityHeadersConfig, provider.web_config.security.headers)
    container.singleton(HSTSConfig, provider.web_config.security.hsts)
    container.singleton(CSPConfig, provider.web_config.security.csp)
    container.singleton(CrossOriginConfig, provider.web_config.security.cross_origin)
    container.singleton(
        CORSMiddlewareFactory,
        CORSMiddlewareFactory(config=provider.web_config.cors),
    )


def register_routing_services(
    container: ContainerRegistrarProtocol,
) -> None:
    """Register routing, filtering, serialization, and background-task services."""
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
    from lexigram.web.routing.router import Router

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


def register_admin_services(
    container: ContainerRegistrarProtocol,
) -> None:
    """Register admin widget handlers and the admin contributor."""
    # Register admin widget handlers (transient for scope safety)
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

    container.transient(ServerStatusWidgetHandler, ServerStatusWidgetHandler)
    container.transient(
        ActiveConnectionsWidgetHandler,
        ActiveConnectionsWidgetHandler,
    )
    container.transient(RequestRateWidgetHandler, RequestRateWidgetHandler)
    container.singleton(WebAdminContributor, WebAdminContributor)


def merge_contributed_extensions(
    provider: WebProvider,
    container: ContainerRegistrarProtocol,
) -> None:
    """Register the contributor registry singleton and merge entry-point contributors."""
    from lexigram.web.contributors import WebContributorRegistry
    from lexigram.web.contributors import discovery as contributor_discovery

    # Register the web contributor registry as a singleton
    container.singleton(WebContributorRegistry, provider._contributor_registry)

    # Discover and merge web contributors from entry-points
    for contributor in contributor_discovery.load_web_contributors():
        provider._contributor_registry.register(contributor)

        # Merge contributed middleware (avoid duplicates)
        for middleware_cls in contributor.get_middleware():
            if middleware_cls not in provider.middleware:
                provider.middleware.append(middleware_cls)

        # Merge contributed controllers (avoid duplicates and
        # subclass-takes-precedence — if a subclass of the contributed
        # controller is already registered, skip the contributed one).
        for controller_cls in contributor.get_controllers():
            if controller_cls not in provider.controllers:
                # Skip if a registered controller is a subclass — the
                # user-supplied override should take precedence over the
                # framework's own controller.
                if isinstance(controller_cls, type) and any(
                    isinstance(ec, type)
                    and ec is not controller_cls
                    and issubclass(ec, controller_cls)
                    for ec in provider.controllers
                ):
                    continue
                provider.controllers.append(controller_cls)


def register_controller_singletons(
    container: ContainerRegistrarProtocol,
    controllers: list[type[Controller]],
) -> None:
    """Register controller classes as container singletons."""
    # Register controllers as singletons if they are classes
    for controller_cls in controllers:
        if isinstance(controller_cls, type):
            container.singleton(controller_cls, controller_cls)


def register_middleware_registries(
    provider: WebProvider,
    container: ContainerRegistrarProtocol,
) -> None:
    """Expose the active middleware pipeline via registry singletons."""
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
    for middleware_cls in provider.middleware:
        cls = (
            middleware_cls if isinstance(middleware_cls, type) else type(middleware_cls)
        )
        middleware_registry.register_middleware(cls)
    container.singleton(MiddlewareRegistry, middleware_registry)
    container.singleton(
        MiddlewareAdapterRegistry,
        MiddlewareAdapterRegistry.with_defaults(),
    )


def register_injectable_services(
    provider: WebProvider,
    container: ContainerRegistrarProtocol,
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
    for cls, scope in provider._extra_injectable_services:
        _register_one(cls, scope)
