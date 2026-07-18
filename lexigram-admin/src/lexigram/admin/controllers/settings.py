"""Spec-driven settings controller for the admin interface.

Renders editable configuration specs (branding, caching, security) through
the config panel UI and persists values to the DB-backed store.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.config import AdminRbacConfig
from lexigram.admin.controllers.base import AdminController
from lexigram.admin.multitenancy.adapter import resolve_tenant_id
from lexigram.admin.rbac.super_admin import is_super_admin
from lexigram.admin.settings.panel import BooleanNode, SecretNode
from lexigram.admin.settings.panel.layout import ConfigLayout
from lexigram.admin.settings.panel.registry import ConfigRegistry
from lexigram.admin.settings.panel.types import ConfigCategory
from lexigram.admin.settings.panel.ui import ConfigDashboardUI
from lexigram.contracts.web import get, post
from lexigram.logging import get_logger
from lexigram.ui import el, render_to_string

if TYPE_CHECKING:
    from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol
    from lexigram.admin.engine.renderer import AdminRenderer
    from lexigram.admin.services.settings_service import AdminSettingsService

logger = get_logger(__name__)

__all__ = ["SettingsController"]


class SettingsController(AdminController):
    """Spec-driven settings controller.

    Routes:
        GET  /admin/settings              - Redirect to first editable spec
        GET  /admin/settings/{namespace}  - Spec edit form
        POST /admin/settings/{namespace}  - Save spec values
    """

    prefix = "/settings"

    def __init__(
        self,
        renderer: AdminRenderer,
        settings_service: AdminSettingsService | None = None,
        csrf_service: AdminCsrfServiceProtocol | None = None,
        audit_service: Any = None,
        registry: ConfigRegistry | None = None,
        rbac_config: AdminRbacConfig | None = None,
    ) -> None:
        super().__init__(renderer=renderer, settings_service=settings_service)
        self._csrf_service = csrf_service
        self._audit_service = audit_service
        self._registry = registry or ConfigRegistry.with_defaults()
        self._rbac_config = rbac_config

    # -- helpers --

    def _store_name(self, spec: type[Any]) -> str:
        """Use the spec's configured store when registered, else the in-memory default."""
        return spec.store_name if self._registry.has_store(spec.store_name) else "default"

    @staticmethod
    def _user_permissions(request: Request) -> frozenset[str]:
        """Return the requesting user's permission set (empty when unknown)."""
        user = getattr(getattr(request, "state", None), "user", None)
        return frozenset(getattr(user, "permissions", None) or ())

    def _user_is_superadmin(self, request: Request) -> bool:
        """Return True when the requesting user holds the superadmin role.

        Superadmin bypasses per-spec permission gating so accounts created
        with an empty permission set (e.g. via the setup wizard) can still
        manage system configurations.
        """
        role = (self._rbac_config or AdminRbacConfig()).super_admin_role
        user = getattr(getattr(request, "state", None), "user", None)
        return is_super_admin(user, role)

    def _build_categories(
        self, request: Request
    ) -> tuple[list[ConfigCategory], list[Any]]:
        """Build one category per package source, with visible specs for the user."""
        permissions = self._user_permissions(request)
        is_superadmin = self._user_is_superadmin(request)

        def _is_visible(spec: Any) -> bool:
            return (
                not spec.required_permissions
                or is_superadmin
                or permissions.issuperset(spec.required_permissions)
            )

        categories: list[ConfigCategory] = []
        visible: list[Any] = []
        for order, package_source in enumerate(self._registry.get_package_sources()):
            specs = [
                spec
                for spec in self._registry.get_specs_by_package(package_source)
                if _is_visible(spec)
            ]
            visible.extend(specs)
            categories.append(
                ConfigCategory(
                    name=package_source,
                    label=package_source.replace("-", " ").replace("_", " ").title(),
                    order=order * 10,
                    specs=specs,
                )
            )
        return categories, visible

    def _get_csrf_token(self, request: Request) -> str | None:
        """Resolve the CSRF token for form rendering, if available."""
        if not self._csrf_service:
            return None
        try:
            session = getattr(request, "session", {})
            session_id: str = session.get("admin_user_id", "")
            return self._csrf_service.generate_token(session_id)
        except Exception:  # noqa: BLE001 — non-fatal for form rendering
            logger.warning("settings.csrf_token_unavailable")
        return None

    async def _audit(
        self,
        request: Request,
        success: bool = True,
        event_type: AdminSecurityEventType = AdminSecurityEventType.SETTINGS_UPDATED,
        **metadata: Any,
    ) -> None:
        """Append a settings change to the security audit log, best-effort."""
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
            logger.warning("settings.audit_failed", **metadata)

    # -- routes --

    @get("/")
    async def index(self, request: Request) -> Response:
        """Redirect to the first editable spec, or render an empty state."""
        categories, visible = self._build_categories(request)
        if visible:
            return RedirectResponse(
                url=f"/admin/settings/{visible[0].namespace}",
                status_code=302,
            )

        layout = ConfigLayout(
            categories=categories,
            active_category=None,
            active_namespace=None,
            content=None,
            title="Settings",
        )
        return await self.render_admin(
            request,
            layout,
            title="Settings",
            breadcrumbs=self.generate_breadcrumbs(
                ("Home", "/admin/"),
                current="Settings",
            ),
        )

    @get("/{namespace:path}")
    async def spec_view(self, request: Request) -> Response:
        """Spec detail/edit view."""
        namespace = request.path_params.get("namespace", "")
        spec = self._registry.get_spec(namespace)
        if not spec or not spec.get_nodes():
            self.flash(f"Configuration '{namespace}' not found.", "error")
            return RedirectResponse(url="/admin/settings", status_code=302)

        permissions = self._user_permissions(request)
        if (
            spec.required_permissions
            and not self._user_is_superadmin(request)
            and not permissions.issuperset(spec.required_permissions)
        ):
            await self._audit(
                request,
                success=False,
                event_type=AdminSecurityEventType.PERMISSION_DENIED,
                reason="permission_denied",
            )
            self.flash("You do not have permission to view this setting.", "error")
            return RedirectResponse(url="/admin/settings", status_code=302)

        categories, _ = self._build_categories(request)
        tenant_id = (
            await resolve_tenant_id(request, default="default")
            if spec.scope == "tenant"
            else None
        )
        values = await self._registry.get_values(
            namespace, self._store_name(spec), tenant_id=tenant_id
        )

        ui = ConfigDashboardUI()
        form_content = ui.render_config_form(
            spec=spec.to_dict(),
            values=values,
            action=f"/admin/settings/{namespace}",
            csrf_token=self._get_csrf_token(request),
        )

        layout = ConfigLayout(
            categories=categories,
            active_category=spec.package_source,
            active_namespace=namespace,
            content=form_content,
            title="Settings",
        )

        return await self.render_admin(
            request,
            layout,
            title=f"{spec.label or namespace} - Settings",
            breadcrumbs=self.generate_breadcrumbs(
                ("Home", "/admin/"),
                ("Settings", "/admin/settings"),
                current=spec.label or namespace,
            ),
        )

    @post("/{namespace:path}")
    async def save_spec(self, request: Request) -> Response:
        """Save configuration changes for a spec."""
        namespace = request.path_params.get("namespace", "")
        spec = self._registry.get_spec(namespace)
        if not spec or not spec.get_nodes():
            self.flash(f"Configuration '{namespace}' not found.", "error")
            return RedirectResponse(url="/admin/settings", status_code=302)

        permissions = self._user_permissions(request)
        if (
            spec.required_permissions
            and not self._user_is_superadmin(request)
            and not permissions.issuperset(spec.required_permissions)
        ):
            await self._audit(
                request,
                success=False,
                event_type=AdminSecurityEventType.PERMISSION_DENIED,
                reason="permission_denied",
            )
            self.flash("You do not have permission to edit this setting.", "error")
            return RedirectResponse(
                url=f"/admin/settings/{namespace}",
                status_code=302,
            )

        form = request.scope.get("admin_form_data")
        if form is None:
            form = await request.form()

        nodes = spec.get_nodes()
        multi = getattr(form, "multi_items", None)
        raw_items = list(multi()) if multi else list(form.items())
        updates = {
            key: (
                "true"
                if isinstance(nodes[key], BooleanNode)
                and any(_value == "on" for _key, _value in raw_items if _key == key)
                else value
            )
            for key, value in raw_items
            if not key.startswith("_") and key in nodes
        }

        ignored_readonly = sorted(key for key in updates if nodes[key].readonly)
        editable_updates = {
            key: value for key, value in updates.items() if not nodes[key].readonly
        }

        cleared_secrets: list[str] = []
        for key in list(editable_updates):
            if isinstance(nodes[key], SecretNode) and not editable_updates[key]:
                editable_updates.pop(key)
                cleared_secrets.append(key)

        invalid = [
            key
            for key, value in editable_updates.items()
            if str(nodes[key].validate(value)).lower() != value.lower()
        ]
        tenant_id = (
            await resolve_tenant_id(request, default="default")
            if spec.scope == "tenant"
            else None
        )
        await self._registry.save_values(
            namespace, editable_updates, self._store_name(spec), tenant_id=tenant_id
        )

        await self._audit(
            request,
            namespace=namespace,
            keys=sorted(editable_updates),
            invalid=invalid,
            ignored_readonly=ignored_readonly,
            cleared_secrets=sorted(cleared_secrets),
        )

        if request.headers.get("hx-request") == "true":
            self._flash_messages.clear()
            if invalid:
                toast_message = (
                    "Settings saved. Invalid values reset to defaults: "
                    + ", ".join(invalid)
                )
                toast_kind = "warning"
            else:
                toast_message = "Settings saved successfully."
                toast_kind = "success"
            toast_html = self._render_toast(toast_message, toast_kind)
            flash_oob = (
                f'<div id="flash-container" hx-swap-oob="true">{toast_html}</div>'
            )

            values = await self._registry.get_values(
                namespace, self._store_name(spec), tenant_id=tenant_id
            )
            ui = ConfigDashboardUI()
            form_content = ui.render_config_form(
                spec=spec.to_dict(),
                values=values,
                action=f"/admin/settings/{namespace}",
                csrf_token=self._get_csrf_token(request),
            )
            form_html = render_to_string(form_content)

            return HTMLResponse(flash_oob + form_html)

        if invalid:
            self.flash(
                f"Saved. Invalid values reset to defaults: {', '.join(invalid)}",
                "warning",
            )
        else:
            self.flash("Settings saved successfully.", "success")
        return RedirectResponse(
            url=f"/admin/settings/{namespace}",
            status_code=302,
        )

    def _render_toast(self, message: str, kind: str) -> str:
        """Build a toast component for htmx responses."""
        return render_to_string(el("div", {"class": f"toast toast-{kind}"}, message))
