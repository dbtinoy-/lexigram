"""Base controller classes for Lexigram Admin.

This module provides base classes that leverage Lexigram's DI container
to provide common functionality to all admin controllers.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import inspect
from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse

from lexigram.admin.auth.models import AdminUser
from lexigram.admin.controllers.route_collection import collect_instance_routes
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.middleware.auth import current_user
from lexigram.concurrency import Parallel
from lexigram.contracts.core import TaskManagerProtocol
from lexigram.contracts.web.controller import ControllerProtocol
from lexigram.di.decorators import inject


@inject
class AdminController(ControllerProtocol):
    """Base async controller for admin pages with authentication and rendering helpers.

    This base class provides:
    - Access to AdminRenderer for rendering pages
    - current_user() helper for auth
    - render_admin() for consistent page rendering (async)
    - Flash message support
    - Breadcrumb generation
    - Parallel async operations
    - Background task scheduling

    All admin controllers should inherit from this to get these features.

    Example:
        ```python
        class MyAdminController(AdminController):
            def __init__(self, renderer: AdminRenderer):
                super().__init__(renderer)

            @get("/admin/dashboard")
            async def dashboard(self, request: Request):
                user = self.current_user(request)
                content = f"Welcome {user.name}!"
                return await self.render_admin(request, content)
        ```
    """

    def __init__(
        self,
        renderer: AdminRenderer,
        task_manager: TaskManagerProtocol | None = None,
        settings_service: Any | None = None,
    ):
        """Initialize admin controller.

        Args:
            renderer: AdminRenderer instance (DI-injected)
            task_manager: TaskManagerProtocol instance (optional)
            settings_service: AdminSettingsService instance (optional), for
                runtime theme overrides (site_name, primary_color).
        """
        self.renderer = renderer
        self.task_manager = task_manager
        self._settings_service = settings_service
        self._flash_messages: list[dict[str, str]] = []

    @classmethod
    def collect_routes(cls) -> list[dict[str, Any]]:
        """Collect routes from controller methods."""
        routes = []
        seen_handlers = set()

        for klass in cls.__mro__:
            if klass is object:
                continue

            for attr_name in dir(klass):
                if attr_name.startswith("_") or attr_name in seen_handlers:
                    continue

                attr_value = getattr(klass, attr_name, None)
                if attr_value is not None and hasattr(attr_value, "_route_config"):
                    route_config = attr_value._route_config
                    routes.append(
                        {
                            "method": route_config["method"],
                            "path": route_config["path"],
                            "handler_name": attr_name,
                            "response_model": route_config.get("response_model"),
                            "request_model": route_config.get("request_model"),
                            "status_code": route_config.get("status_code", 200),
                            "summary": route_config.get("summary"),
                            "description": route_config.get("description"),
                            "tags": route_config.get("tags"),
                            "operation_id": route_config.get("operation_id"),
                            "responses": route_config.get("responses"),
                            "deprecated": route_config.get("deprecated", False),
                        }
                    )
                    seen_handlers.add(attr_name)

        return routes

    def current_user(self, request: Request) -> AdminUser:
        """Get the current authenticated user.

        Args:
            request: The current request

        Returns:
            AdminUser instance or GUEST_USER if not authenticated
        """
        return current_user(request)  # type: ignore[return-value]

    async def _apply_theme_overrides(
        self,
        request: Request,
        extra_context: dict[str, Any],
    ) -> None:
        """Load runtime theme settings and merge into extra_context.

        Uses the controller's settings service when injected, otherwise
        builds one from the request-scoped DI container (mirroring the
        bundle's own construction) so every renderer path honors the same
        persisted branding.
        """
        if not self._settings_service:
            try:
                from lexigram.admin.services.settings_service import (
                    resolve_admin_settings_service,
                )

                container = getattr(request.state, "container", None) or getattr(
                    request.app.state, "container", None
                )
                if container is not None:
                    self._settings_service = await resolve_admin_settings_service(
                        container
                    )
            except Exception:  # noqa: BLE001, S110 — non-fatal
                pass
        if not self._settings_service:
            return
        try:
            from lexigram.admin.multitenancy.adapter import resolve_tenant_id

            tenant = await resolve_tenant_id(request, default="default")
            overrides = await self._settings_service.get_all(tenant)
            for field in (
                "primary_color",
                "site_name",
                "logo_url",
                "favicon_url",
                "dark_mode",
            ):
                value = overrides.get(field) or overrides.get(f"admin.branding.{field}")
                if value:
                    extra_context.setdefault(field, value)
        except Exception:  # noqa: BLE001, S110 — non-fatal
            pass

    async def _apply_tenant_context(
        self,
        request: Request,
        extra_context: dict[str, Any],
    ) -> None:
        """Resolve current tenant + switchable list into extra_context.

        Populates ``current_tenant_id``/``current_tenant_name``/
        ``tenant_list``/``tenant_csrf_token`` only when tenancy is enabled
        and the requesting user is a superadmin — presence of
        ``current_tenant_id`` doubles as the render gate for
        ``TenantSwitcher`` (absent means "don't show the switcher"), so no
        separate flag is threaded through.

        ``tenant_csrf_token`` is generated fresh via the CSRF service
        rather than reusing ``request.state.csrf_token``, because that
        value is only populated by resource CRUD form rendering
        (``resources/form_renderer.py``, ``resources/handler.py``), not on
        the dashboard/widget pages this switcher actually appears on.
        """
        try:
            from lexigram.admin.config import AdminConfig

            container = getattr(request.state, "container", None) or getattr(
                request.app.state, "container", None
            )
            if container is None:
                return
            config = await container.resolve(AdminConfig)
            if not config.tenancy.enabled:
                return

            user = getattr(request.state, "user", None)
            if not user:
                return

            from lexigram.admin.rbac.super_admin import is_super_admin

            if not is_super_admin(user, config.rbac.super_admin_role):
                return

            from lexigram.admin.multitenancy.adapter import (
                TenantProviderRegistry,
                resolve_tenant_id,
            )

            registry = await container.resolve(TenantProviderRegistry)
            current_tenant_id = await resolve_tenant_id(request, default="default")
            current_tenant = await registry.get(current_tenant_id)
            extra_context.setdefault("current_tenant_id", current_tenant_id)
            extra_context.setdefault(
                "current_tenant_name",
                current_tenant.name if current_tenant else current_tenant_id,
            )
            extra_context.setdefault(
                "tenant_list",
                [(t.tenant_id, t.name) for t in await registry.all(active_only=True)],
            )

            try:
                from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol

                csrf_service = await container.resolve(AdminCsrfServiceProtocol)
                session = getattr(request, "session", {})
                session_id = session.get("admin_user_id", "")
                extra_context.setdefault(
                    "tenant_csrf_token", csrf_service.generate_token(session_id)
                )
            except Exception:  # noqa: BLE001, S110 — token generation is non-fatal
                pass
        except Exception:  # noqa: BLE001, S110 — matches _apply_theme_overrides
            pass

    async def _apply_impersonation_context(
        self,
        request: Request,
        extra_context: dict[str, Any],
    ) -> None:
        """Populate impersonation banner state into extra_context, if active.

        Resolves ``ImpersonationService`` from the request-scoped container
        and checks whether the current actor has an active session. Display
        name resolution is out of scope (no user-store dependency here) —
        the banner shows the raw target user ID.
        """
        user = getattr(request.state, "user", None)
        if user is None:
            return

        try:
            from lexigram.admin.services.impersonation import ImpersonationService

            container = getattr(request.state, "container", None) or getattr(
                request.app.state, "container", None
            )
            if container is None:
                return
            service = await container.resolve(ImpersonationService)
            if service is None:
                return

            actor_id = str(getattr(user, "id", ""))
            session = service.get_active_session(actor_id, request)
            if session is not None:
                extra_context.setdefault("impersonation_active", True)
                extra_context.setdefault(
                    "impersonation_target_id", session.target_user_id
                )
        except Exception:  # noqa: BLE001, S110 — non-fatal
            pass

    async def render_admin(
        self,
        request: Request,
        content: Any,
        title: str = "Admin",
        breadcrumbs: list[dict[str, Any]] | None = None,
        **extra_context: Any,
    ) -> HTMLResponse:
        """Render content within admin shell (async).

        Args:
            request: The current request
            content: Content to render (Component or HTML string)
            title: Page title
            breadcrumbs: List of breadcrumb dicts
            **extra_context: Additional context passed to the renderer.

        Returns:
            HTMLResponse with rendered admin page
        """
        # Inject runtime theme overrides (primary_color, site_name)
        await self._apply_theme_overrides(request, extra_context)
        # Inject tenant context (current tenant, switchable list, CSRF token)
        await self._apply_tenant_context(request, extra_context)
        # Inject impersonation banner state, if an active session exists
        await self._apply_impersonation_context(request, extra_context)

        # If content is awaitable, resolve it first
        if inspect.isawaitable(content):
            content = await content

        # Check for HTMX request targeting #main-content
        is_htmx = request.headers.get("HX-Request") == "true"
        target = request.headers.get("HX-Target")

        if is_htmx and target == "main-content":
            # Only return the partial content
            return self.renderer.render_partial(content)

        return self.renderer.render_page(
            content,
            request=request,
            title=title,
            breadcrumbs=breadcrumbs,
            **extra_context,
        )

    def flash(self, message: str, category: str = "info") -> None:
        """Add a flash message to be displayed on next page.

        Args:
            message: Message text
            category: Message category (info, success, warning, error)
        """
        self._flash_messages.append({"message": message, "category": category})

    def get_flash_messages(self) -> list[dict[str, str]]:
        """Get and clear flash messages.

        Returns:
            List of flash message dicts
        """
        messages = self._flash_messages.copy()
        self._flash_messages.clear()
        return messages

    def generate_breadcrumbs(
        self,
        *crumbs: tuple[str, str],
        current: str | None = None,
    ) -> list[dict[str, str]]:
        """Generate breadcrumb navigation.

        Args:
            *crumbs: Variable number of (label, url) tuples
            current: Label for current page (no link)

        Returns:
            List of breadcrumb dicts with 'label' and 'url' keys

        Example:
            ```python
            breadcrumbs = self.generate_breadcrumbs(
                ("Home", "/admin/"),
                ("Users", "/admin/users"),
                current="Edit User"
            )
            ```
        """
        result = []

        for label, url in crumbs:
            result.append({"label": label, "url": url})

        if current:
            result.append({"label": current, "url": ""})

        return result

    def build_specification(self, request: Request, allowed_fields: list[str]) -> Any:
        """Build a specification from request query parameters.

        Args:
            request: The request
            allowed_fields: List of fields allowed to be filtered

        Returns:
            SpecificationProtocol or None
        """
        from lexigram.admin.lib.specifications import (
            AndSpecification,
            FieldSpecification,
        )

        specs = []
        for field in allowed_fields:
            if value := request.query_params.get(field):
                specs.append(FieldSpecification(field, value))  # type: ignore[abstract]

        if not specs:
            return None

        if len(specs) == 1:
            return specs[0]

        return AndSpecification(*specs)

    async def parallel_fetch(
        self,
        *callables: Callable[[], Awaitable[Any]],
    ) -> list[Any]:
        """Fetch multiple async operations in parallel.

        Args:
            *callables: Async functions to execute concurrently

        Returns:
            List of results in same order as input

        Example:
            ```python
            users, posts, comments = await self.parallel_fetch(
                lambda: user_service.list(),
                lambda: post_service.list(),
                lambda: comment_service.list(),
            )
            ```
        """
        results = await Parallel.gather(*(fn() for fn in callables))
        return list(results)

    async def background_task(
        self,
        task: Callable[[], Awaitable[Any]],
        name: str | None = None,
    ) -> None:
        """Schedule task to run in background without blocking response.

        Args:
            task: Async function to run in background
            name: Optional task name for tracking

        Example:
            ```python
            # Send email in background
            await self.background_task(
                lambda: email_service.send(user, "Welcome!"),
                name="welcome_email"
            )
            # Response returns immediately
            ```
        """
        # Use central TaskManager for background tasks
        self.task_manager.create_background_task(task(), name=name)  # type: ignore[union-attr]

    def get_routes(self) -> list[Any]:
        """Extract decorated routes from this controller instance."""
        return collect_instance_routes(self)
