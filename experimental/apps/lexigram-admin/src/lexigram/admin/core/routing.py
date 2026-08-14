from __future__ import annotations

from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from lexigram.admin.auth.services._cookie_config import (
    build_session_cookie_kwargs,
)
from lexigram.admin.config import AdminConfig
from lexigram.admin.controllers.command_palette import CommandPaletteController
from lexigram.admin.controllers.search import SearchController
from lexigram.admin.openapi.controller import OpenAPIController
from lexigram.admin.relations.routes import register_relation_routes
from lexigram.admin.resources.handler import ResourceHandler
from lexigram.admin.services.search_service import SearchService
from lexigram.contracts.auth import AuthorizerProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


class _ResourceManager:
    """Adapter that wraps a ``{name: resource_instance}`` dict for SearchService.

    SearchService expects a ``resource_manager`` with a ``get_all_resources()``
    method that returns resource instances.  This adapter provides that
    interface from the AdminRouter's internal resources dict.
    """

    def __init__(self, resources: dict[str, Any]) -> None:
        self._resources = resources

    def get_all_resources(self) -> list[Any]:
        return list(self._resources.values())


@inject
class AdminRouter:
    """Router and mounting logic for the admin panel."""

    def __init__(
        self,
        config: AdminConfig,
        resources: dict[str, Any] | None = None,
        controllers: list[Any] | None = None,
        middleware_stack: list[tuple[type, dict]] | None = None,
        authorizer: AuthorizerProtocol | None = None,
    ):
        self._config = config
        self._resources = resources or {}
        self._controllers = controllers or []
        self._middleware_stack = middleware_stack or []
        self._authorizer = authorizer
        self._extra_routes: list[Route] = []
        self._is_mounted = False

    def add_route(
        self,
        path: str,
        method: str,
        handler: Any,
        name: str,
    ) -> None:
        """Register a single route for later mounting.

        Routes added here are included the next time ``mount()`` is called.
        """
        self._extra_routes.append(
            Route(
                path,
                endpoint=handler,
                methods=[method],
                name=name,
            ),
        )

    def alias_route(self, source_path: str, alias_path: str, name: str) -> bool:
        """Register ``alias_path`` with the same endpoint as ``source_path``.

        Used to expose a route under an additional path (e.g. cluster
        areas under the center namespace). Returns ``True`` when the
        source route was found and aliased.

        Args:
            source_path: Path of the already-registered route.
            alias_path: Additional path to register.
            name: Route name for the alias.

        Returns:
            Whether the source route existed and the alias was added.
        """
        source = next(
            (r for r in self._extra_routes if r.path == source_path),
            None,
        )
        if source is None:
            return False
        self._extra_routes.append(
            Route(
                alias_path,
                endpoint=source.endpoint,
                methods=source.methods,
                name=name,
            ),
        )
        return True

    def mount(self, app: Starlette) -> Starlette | None:
        """Mount admin panel to a Starlette application.

        Returns:
            The created admin sub-app (so callers can set state on it), or None
            if mounting failed.
        """
        if self._is_mounted:
            logger.warning("AdminRouter already mounted, skipping")
            return None

        routes = self._build_routes()
        admin_app = Starlette(routes=routes)

        # Sign the admin session cookie from the validated auth config. The
        # helper also derives https_only / same_site / max_age from env.
        cookie_kwargs = build_session_cookie_kwargs(self._config.auth)
        # Add our middleware in reverse order so that the stack list order
        # (e.g. [Setup, Csrf, AuthGuard]) becomes the execution order.
        # Starlette's add_middleware inserts at position 0 (outermost), so
        # to get Session → Setup → Csrf → AuthGuard → Routes we must:
        #   1. add AuthGuard first  (innermost)
        #   2. add Csrf
        #   3. add Setup
        #   4. add Session last     (outermost — runs first, populates scope["session"])
        for middleware_class, options in reversed(self._middleware_stack):
            admin_app.add_middleware(middleware_class, **options)  # type: ignore[arg-type]

        admin_app.add_middleware(SessionMiddleware, **cookie_kwargs)

        admin_mount = Mount(
            self._config.prefix,
            app=admin_app,
            name="admin",
        )

        if hasattr(app, "routes"):
            app.routes.append(admin_mount)
        elif hasattr(app, "include_router"):
            app.include_router(admin_mount)
        elif hasattr(app, "_invoker"):
            invoker = app._invoker
            if hasattr(invoker, "routes"):
                invoker.routes.append(admin_mount)
            else:
                logger.warning("Could not mount admin - Lexigram invoker has no routes")
                return None
        else:
            logger.warning("Could not mount admin - unknown app type")
            return None

        self._is_mounted = True
        logger.info("admin.mounted", prefix=self._config.prefix)
        return admin_app

    def _build_routes(self) -> list[Route | Mount]:
        """Build all admin routes."""
        routes: list[Route | Mount] = []

        static_dir = self._resolve_static_dir()
        if static_dir and static_dir.exists():
            routes.append(
                Mount(
                    "/static",
                    app=StaticFiles(directory=str(static_dir)),
                    name="admin_static",
                ),
            )

        for controller in self._controllers:
            if not isinstance(controller, type) and hasattr(controller, "get_routes"):
                routes.extend(controller.get_routes())

        for name, resource in self._resources.items():
            routes.extend(self._build_resource_routes(name, resource))

        # Global search endpoint
        search_service = SearchService(
            resource_manager=_ResourceManager(self._resources),
            authorizer=self._authorizer,
        )
        search_controller = SearchController(search_service=search_service)
        routes.append(
            Route(
                "/search",
                endpoint=search_controller.search,
                methods=["GET"],
                name="admin_search",
            ),
        )

        # Command palette endpoint
        palette_controller = CommandPaletteController(search_service=search_service)
        routes.append(
            Route(
                "/command-palette",
                endpoint=palette_controller.search,
                methods=["GET"],
                name="admin_command_palette",
            ),
        )

        # OpenAPI spec endpoint
        openapi_controller = OpenAPIController(resources=self._resources)
        routes.append(
            Route(
                "/openapi.json",
                endpoint=openapi_controller.get_spec,
                methods=["GET"],
                name="admin_openapi",
            ),
        )

        # Extra routes registered via add_route (e.g. from RouteIntegrator)
        routes.extend(self._extra_routes)

        return routes

    def _build_resource_routes(
        self,
        name: str,
        resource: Any | None = None,
    ) -> list[Route]:
        """Build routes for a resource."""
        prefix = f"/{name}"
        # Pass the resource in a single-entry dict so ResourceHandler can look it up
        resources_dict = {name: resource} if resource is not None else {}
        routes: list[Route] = [
            Route(
                prefix,
                ResourceHandler(self._config, name, "list", resources=resources_dict),
                name=f"admin_{name}_list",
            ),
            Route(
                f"{prefix}/create",
                ResourceHandler(self._config, name, "create", resources=resources_dict),
                name=f"admin_{name}_create",
                methods=["GET", "POST"],
            ),
            Route(
                f"{prefix}/create/form",
                ResourceHandler(self._config, name, "create", resources=resources_dict),
                name=f"admin_{name}_create_form",
            ),
            # Fixed-path routes must come before {prefix}/{id} to avoid
            # the catch-all parameterised route stealing them.
            Route(
                f"{prefix}/bulk",
                ResourceHandler(self._config, name, "bulk", resources=resources_dict),
                name=f"admin_{name}_bulk",
                methods=["POST"],
            ),
            Route(
                f"{prefix}/bulk-delete-confirm",
                ResourceHandler(
                    self._config, name, "bulk-delete-confirm", resources=resources_dict
                ),
                name=f"admin_{name}_bulk_delete_confirm",
                methods=["GET"],
            ),
            Route(
                f"{prefix}/bulk-purge-confirm",
                ResourceHandler(
                    self._config, name, "bulk-purge-confirm", resources=resources_dict
                ),
                name=f"admin_{name}_bulk_purge_confirm",
                methods=["GET"],
            ),
            Route(
                f"{prefix}/bulk-restore-confirm",
                ResourceHandler(
                    self._config, name, "bulk-restore-confirm", resources=resources_dict
                ),
                name=f"admin_{name}_bulk_restore_confirm",
                methods=["GET"],
            ),
            Route(
                f"{prefix}/import-example",
                ResourceHandler(
                    self._config, name, "import-example", resources=resources_dict
                ),
                name=f"admin_{name}_import_example",
                methods=["GET"],
            ),
            Route(
                f"{prefix}/import-report",
                ResourceHandler(
                    self._config, name, "import-report", resources=resources_dict
                ),
                name=f"admin_{name}_import_report",
                methods=["GET"],
            ),
            Route(
                f"{prefix}/{{id}}",
                ResourceHandler(self._config, name, "detail", resources=resources_dict),
                name=f"admin_{name}_detail",
            ),
            Route(
                f"{prefix}/{{id}}/edit",
                ResourceHandler(self._config, name, "edit", resources=resources_dict),
                name=f"admin_{name}_edit",
                methods=["GET", "POST"],
            ),
            Route(
                f"{prefix}/{{id}}/clone",
                ResourceHandler(self._config, name, "clone", resources=resources_dict),
                name=f"admin_{name}_clone",
                methods=["GET"],
            ),
            Route(
                f"{prefix}/{{id}}/restore",
                ResourceHandler(
                    self._config, name, "restore", resources=resources_dict
                ),
                name=f"admin_{name}_restore",
                methods=["GET"],
            ),
            Route(
                f"{prefix}/{{id}}/purge",
                ResourceHandler(self._config, name, "purge", resources=resources_dict),
                name=f"admin_{name}_purge",
                methods=["GET"],
            ),
            Route(
                f"{prefix}/{{id}}/delete-confirm",
                ResourceHandler(
                    self._config, name, "delete-confirm", resources=resources_dict
                ),
                name=f"admin_{name}_delete_confirm",
                methods=["GET"],
            ),
            Route(
                f"{prefix}/{{id}}/delete",
                ResourceHandler(self._config, name, "delete", resources=resources_dict),
                name=f"admin_{name}_delete",
                methods=["DELETE", "POST"],
            ),
            Route(
                f"{prefix}/{{id}}/permissions",
                ResourceHandler(
                    self._config, name, "permissions", resources=resources_dict
                ),
                name=f"admin_{name}_permissions",
                methods=["GET", "POST"],
            ),
        ]

        # Register relation routes for each RelationManager on this resource
        if (
            resource is not None
            and hasattr(resource, "relations")
            and resource.relations
        ):
            for rel_cls in resource.relations:
                rel_routes = register_relation_routes(
                    name,
                    rel_cls,
                    parent_data_source=getattr(resource, "_data_source", None),
                )
                routes.extend(rel_routes)

        return routes

    def _resolve_static_dir(self) -> Path | None:
        """Resolve static files directory."""
        if self._config.static_dir:
            return Path(self._config.static_dir)

        package_dir = Path(__file__).parent.parent
        default_static = package_dir / "static"
        if default_static.exists():
            return default_static

        return None
