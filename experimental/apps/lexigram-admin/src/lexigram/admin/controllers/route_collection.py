"""Starlette route materialization for admin controller instances."""

from __future__ import annotations

import inspect
from typing import Any

from starlette.requests import Request
from starlette.routing import Route


def collect_instance_routes(controller: Any) -> list[Any]:
    """Extract decorated routes from a controller instance."""
    routes = []

    # In lexigram-web, decorated methods have _route_config
    for name, method in inspect.getmembers(controller, predicate=inspect.ismethod):
        if hasattr(method, "_route_config"):
            config = method._route_config
            # We use the Router._create_endpoint logic to wrap the handler
            # but since we already have an instance, we can simplify/adapt

            # Mock a container or just wrap the method directly?
            # The Router normally wants a class and method name to resolve from container.
            # But here we already have the instance.

            # Let's create a compatible Starlette handler
            async def starlette_handler(request: Request, m=method) -> Any:
                # We need to handle parameters like Router does
                # For simplicity, we can reuse Router._create_endpoint logic
                # Or just call the method if signature allows
                sig = inspect.signature(m)
                if "request" in sig.parameters:
                    return await m(request=request)
                return await m()

            # Prepend controller prefix to the route path
            base_path = getattr(controller, "prefix", "").rstrip("/")
            route_path = config["path"]
            if not route_path.startswith("/"):
                route_path = f"/{route_path}"

            if route_path == "/" and base_path:
                full_path = base_path
            else:
                full_path = f"{base_path}{route_path}"

            if not full_path:
                full_path = "/"

            routes.append(
                Route(
                    full_path,
                    endpoint=starlette_handler,
                    methods=[config["method"]],
                    name=config.get("name") or f"admin_custom_{name}",
                ),
            )

    # Also check for 'index' method if no explicit route matches prefix
    if hasattr(controller, "index") and not any(r.path == "/" for r in routes):

        async def index_handler(request: Request) -> Any:
            return await controller.index(request)

        routes.append(
            Route(
                "/",
                endpoint=index_handler,
                methods=["GET"],
                name="admin_custom_index",
            ),
        )

    return routes
