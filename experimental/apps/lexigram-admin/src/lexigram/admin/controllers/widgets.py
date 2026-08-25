"""Widget controller — routes HTMX widget requests to contributors."""

from __future__ import annotations

import inspect
from typing import Any

from starlette.requests import Request
from starlette.routing import Route

from lexigram.admin.auth.protocols import (
    AdminAuditLogServiceProtocol,
    AdminCsrfServiceProtocol,
)
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.config import AdminRbacConfig
from lexigram.admin.controllers.widget_content_handlers import (
    render_health_check_fragment,
    render_widget_fragment,
)
from lexigram.admin.controllers.widget_customize_handlers import (
    render_customize_panel,
    save_all_configs,
)
from lexigram.admin.controllers.widget_handler_support import csrf_token_for
from lexigram.admin.controllers.widget_pref_handlers import (
    render_config_popup,
    reorder,
    save_config,
)
from lexigram.admin.multitenancy.adapter import resolve_tenant_id
from lexigram.admin.rbac.super_admin import is_super_admin
from lexigram.contracts.admin.protocols import AdminContributorRegistryProtocol
from lexigram.contracts.web import get, post
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)

_REQUIRED_PERMISSIONS = frozenset({"admin.settings.edit"})


@inject
class WidgetController:
    """Routes HTMX widget/health requests to the appropriate contributor.

    All dependencies are constructor-injected. No service locator.

    Args:
        registry: The admin contributor registry.
    """

    prefix = ""

    def __init__(
        self,
        registry: AdminContributorRegistryProtocol,
        audit_service: AdminAuditLogServiceProtocol | None = None,
        csrf_service: AdminCsrfServiceProtocol | None = None,
        rbac_config: AdminRbacConfig | None = None,
    ) -> None:
        self._registry = registry
        self._settings_service: Any = None
        self._resolver: Any = None
        self._audit_service = audit_service
        self._csrf_service = csrf_service
        self._rbac_config = rbac_config

    # -- helpers --

    def _user_has_edit_permission(self, request: Request) -> bool:
        """Check whether the requesting user may mutate widget prefs.

        Superadmin bypasses permission gating so accounts created with an
        empty permission set (e.g. via the setup wizard) can still manage
        dashboard widgets.
        """
        user = getattr(getattr(request, "state", None), "user", None)
        if self._user_is_superadmin(request):
            return True
        permissions = frozenset(getattr(user, "permissions", None) or ())
        return permissions.issuperset(_REQUIRED_PERMISSIONS)

    def _user_permissions(self, request: Request) -> frozenset[str]:
        """Return the requesting user's permission set (empty when absent)."""
        user = getattr(getattr(request, "state", None), "user", None)
        return frozenset(getattr(user, "permissions", None) or ())

    def _user_is_superadmin(self, request: Request) -> bool:
        """Return True when the requesting user holds the superadmin role."""
        role = (self._rbac_config or AdminRbacConfig()).super_admin_role
        user = getattr(getattr(request, "state", None), "user", None)
        return bool(user) and is_super_admin(user, role)

    def _has_required_permission(self, request: Request, required: str | None) -> bool:
        """Check *required* against the requesting user; superadmin bypasses."""
        if not required:
            return True
        if self._user_is_superadmin(request):
            return True
        return required in self._user_permissions(request)

    async def _audit(
        self,
        request: Request,
        success: bool = True,
        event_type: AdminSecurityEventType = AdminSecurityEventType.SETTINGS_UPDATED,
        **metadata: Any,
    ) -> None:
        """Append a widget-prefs change to the security audit log, best-effort."""
        if not self._audit_service:
            return
        try:
            client = getattr(request, "client", None)
            await self._audit_service.log_event(
                event_type=event_type,
                ip_address=getattr(client, "host", "unknown"),
                user_agent=request.headers.get("user-agent", "") or "",
                success=success,
                metadata=metadata,
            )
        except Exception:  # noqa: BLE001 — audit failures must not break saves
            logger.warning("widgets.audit_failed", **metadata)

    def get_routes(self) -> list[Any]:
        """Extract decorated routes from this controller instance."""
        routes = []

        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, "_route_config"):
                config = method._route_config
                method_params = list(inspect.signature(method).parameters.keys())

                async def starlette_handler(
                    request: Request, m=method, params=method_params
                ) -> Any:
                    kwargs = {"request": request}
                    for param in params:
                        if param == "request":
                            continue
                        if param in request.path_params:
                            kwargs[param] = request.path_params[param]
                    return await m(**kwargs)

                base_path = getattr(self, "prefix", "").rstrip("/")
                route_path = config["path"]
                if not route_path.startswith("/"):
                    route_path = f"/{route_path}"

                if route_path == "/" and base_path:
                    full_path = base_path
                else:
                    full_path = f"{base_path}{route_path}" if base_path else route_path

                routes.append(
                    Route(
                        full_path,
                        endpoint=starlette_handler,
                        methods=[config["method"]],
                        name=config.get("name") or f"admin_widget_{name}",
                    ),
                )

        return routes

    @get("/{contributor_id}/widgets/{widget_name}")
    async def render_widget(
        self,
        request: Request,
        contributor_id: str,
        widget_name: str,
    ) -> object:
        """Render a widget fragment for the HTMX dashboard."""
        return await render_widget_fragment(
            request,
            contributor_id=contributor_id,
            widget_name=widget_name,
            registry=self._registry,
            settings_service=self._settings_service,
            resolver=self._resolver,
            resolve_tenant=resolve_tenant_id,
            has_permission=self._has_required_permission,
        )

    @get("/{contributor_id}/health/{check_name}")
    async def render_health_check(
        self,
        request: Request,
        contributor_id: str,
        check_name: str,
    ) -> object:
        """Render a health check fragment for the HTMX dashboard."""
        return await render_health_check_fragment(
            request,
            contributor_id=contributor_id,
            check_name=check_name,
            registry=self._registry,
            has_permission=self._has_required_permission,
        )

    @get("/core/widgets/{name}/config")
    async def widget_config_popup(self, request: Request, name: str) -> object:
        """Render config popup for a widget."""
        return await render_config_popup(
            request,
            name=name,
            registry=self._registry,
            settings_service=self._settings_service,
            resolve_tenant=resolve_tenant_id,
            user_has_edit_permission=self._user_has_edit_permission,
            audit=self._audit,
        )

    @post("/core/widgets/config")
    async def save_widget_config(self, request: Request) -> object:
        """Save a single widget's configuration."""
        return await save_config(
            request,
            settings_service=self._settings_service,
            resolve_tenant=resolve_tenant_id,
            user_has_edit_permission=self._user_has_edit_permission,
            audit=self._audit,
        )

    @post("/core/widgets/reorder")
    async def reorder_widgets(self, request: Request) -> object:
        """Save widget order after drag-and-drop."""
        return await reorder(
            request,
            settings_service=self._settings_service,
            resolve_tenant=resolve_tenant_id,
            user_has_edit_permission=self._user_has_edit_permission,
            audit=self._audit,
        )

    @get("/core/widgets/customize")
    async def customize_all_widgets(self, request: Request) -> object:
        """Render full dashboard customization panel with all widgets."""
        return await render_customize_panel(
            request,
            registry=self._registry,
            settings_service=self._settings_service,
            resolve_tenant=resolve_tenant_id,
            csrf_token=csrf_token_for(self._csrf_service, request),
            user_has_edit_permission=self._user_has_edit_permission,
            audit=self._audit,
        )

    @post("/core/widgets/customize/save")
    async def save_all_widget_configs(self, request: Request) -> object:
        """Save all widget configurations from the customize panel."""
        return await save_all_configs(
            request,
            registry=self._registry,
            settings_service=self._settings_service,
            resolve_tenant=resolve_tenant_id,
            user_has_edit_permission=self._user_has_edit_permission,
            audit=self._audit,
        )


__all__ = ["WidgetController"]
