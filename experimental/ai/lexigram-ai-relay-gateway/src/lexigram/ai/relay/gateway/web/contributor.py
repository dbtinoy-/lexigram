"""Web contributor mounting the relay gateway's raw Starlette routes.

The gateway package cannot import lexigram-web controller classes, so
``get_controllers`` is empty and the inbound relay routes are mounted
directly on the host application in ``mount_to_app``.  The gateway
implementation is resolved from the request-scoped DI container at
request time.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.gateway.catalog import ModelCatalogService
from lexigram.ai.relay.gateway.operations.health import RelayHealthService
from lexigram.ai.relay.gateway.passthrough import PassthroughService
from lexigram.ai.relay.gateway.web.routes import build_routes
from lexigram.contracts.ai.relay import RelayGatewayProtocol
from lexigram.contracts.exceptions.container import ContainerError

__all__ = ["RelayGatewayWebContributor"]


class RelayGatewayWebContributor:
    """Web contributor for the relay gateway.

    Implements the ``WebContributorProtocol`` surface duck-typed: the
    contributor id is ``"relay-gateway"``, no controllers or middleware
    are contributed (controller classes are lexigram-web types), and the
    four inbound relay routes are mounted on the Starlette application.
    Repeated mounts are idempotent: a path already present in
    ``app.routes`` is skipped.
    """

    @property
    def contributor_id(self) -> str:
        """Return the unique contributor identifier.

        Returns:
            The string ``"relay-gateway"``.
        """
        return "relay-gateway"

    def get_controllers(self) -> list[type[Any]]:
        """Return the controller classes contributed by the gateway.

        Controller classes are lexigram-web types, which the gateway
        package cannot import; raw Starlette routes are mounted in
        ``mount_to_app`` instead.

        Returns:
            An empty list.
        """
        return []

    def get_middleware(self) -> list[type[Any]]:
        """Return the middleware classes contributed by the gateway.

        Middleware is contributed by the host application, not the
        gateway.

        Returns:
            An empty list.
        """
        return []

    async def mount_to_app(self, app: Any, container: object) -> None:
        """Mount the four inbound relay routes on *app*.

        The gateway is resolved per request: the request-scoped
        container from ``request.state.container`` is preferred, falling
        back to the mount-time container.  Routes already present in
        ``app.routes`` are skipped so repeated mounts never duplicate
        paths.

        Args:
            app: The ASGI application (typically Starlette) to mount
                routes on.
            container: The DI container used as fallback resolution.
        """

        async def _resolve(request: Any) -> RelayGatewayProtocol:
            request_container: Any = (
                getattr(request.state, "container", None) or container
            )
            return await request_container.resolve(RelayGatewayProtocol)

        async def _resolve_passthrough(request: Any) -> PassthroughService:
            request_container: Any = (
                getattr(request.state, "container", None) or container
            )
            return await request_container.resolve(PassthroughService)

        async def _resolve_model_catalog(request: Any) -> ModelCatalogService:
            request_container: Any = (
                getattr(request.state, "container", None) or container
            )
            return await request_container.resolve(ModelCatalogService)

        async def _resolve_health(request: Any) -> RelayHealthService | None:
            request_container: Any = (
                getattr(request.state, "container", None) or container
            )
            try:
                return await request_container.resolve_optional(RelayHealthService)
            except (ContainerError, AttributeError):
                return None

        routes = build_routes(
            _resolve,
            resolve_passthrough=_resolve_passthrough,
            resolve_model_catalog=_resolve_model_catalog,
            resolve_health=_resolve_health,
            fallback_container=container,
        )
        for route in routes:
            path = route.path
            if any(
                getattr(existing, "path", None) == path
                for existing in getattr(app, "routes", [])
            ):
                continue
            app.add_route(
                path, route.endpoint, methods=sorted(route.methods or ["POST"])
            )
