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
from lexigram.admin.controllers.settings_history import SettingsHistoryMixin
from lexigram.admin.multitenancy.adapter import resolve_tenant_id
from lexigram.admin.rbac.super_admin import is_super_admin
from lexigram.admin.resources.urls import (
    admin_prefix_from_request,
    admin_url,
    mount_admin_url,
)
from lexigram.admin.settings.conflict import SettingsConflictError
from lexigram.admin.settings.panel import BooleanNode, SecretNode
from lexigram.admin.settings.panel.layout import ConfigLayout
from lexigram.admin.settings.panel.registry import ConfigRegistry
from lexigram.admin.settings.panel.types import ConfigCategory, PanelLink
from lexigram.admin.settings.panel.ui import ConfigDashboardUI
from lexigram.admin.settings.revision import (
    extract_submitted_revision,
    revision_matches,
    settings_revision,
)
from lexigram.admin.settings.snapshots import SettingsSnapshotService
from lexigram.contracts.web import get, post
from lexigram.logging import get_logger
from lexigram.ui import ServerToastChannel, ToastData, el, render_to_string

if TYPE_CHECKING:
    from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol
    from lexigram.admin.engine.renderer import AdminRenderer
    from lexigram.admin.services.settings_service import AdminSettingsService

logger = get_logger(__name__)

__all__ = ["SettingsController"]


class SettingsController(SettingsHistoryMixin, AdminController):
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
        snapshot_service: SettingsSnapshotService | None = None,
        dashboard: Any = None,
        application_config: Any = None,
        config_loader: Any = None,
    ) -> None:
        super().__init__(renderer=renderer, settings_service=settings_service)
        self._csrf_service = csrf_service
        self._audit_service = audit_service
        self._registry = registry or ConfigRegistry.with_defaults()
        self._application_config = application_config
        self._config_loader = config_loader
        if application_config is not None:
            # Keep the effective application configuration in the same
            # permission-filtered sidebar as editable specs, but bind it to a
            # read-only store so it can never become a second write path.
            from lexigram.admin.settings.application import (
                AdminConfigStore,
                EffectiveApplicationConfigSpec,
            )

            self._registry.register_store(
                "application", AdminConfigStore(application_config, config_loader)
            )
            self._registry.register_spec(EffectiveApplicationConfigSpec)
        self._rbac_config = rbac_config
        # History is on by default so a mistaken save is always recoverable;
        # pass an explicit store via DI to make it durable across restarts.
        self._snapshots = snapshot_service or SettingsSnapshotService()
        # Duck-typed provider with `async get_settings_panels(user)` (the
        # DashboardAssembler singleton) — surfaces contributor panels such
        # as System Info in the sidebar (R50, doc 46). Optional: without it
        # the sidebar is spec-only, exactly as before.
        self._dashboard = dashboard

    # -- helpers --

    def _store_name(self, spec: type[Any]) -> str:
        """Use the spec's configured store when registered, else the in-memory default."""
        return (
            spec.store_name if self._registry.has_store(spec.store_name) else "default"
        )

    @staticmethod
    async def _tenant_for_spec(request: Request, spec: type[Any]) -> str | None:
        """Resolve tenant scope while keeping the default tenant backward-compatible.

        The DB adapter already maps ``None`` to its constructor's default
        tenant. Treating the conventional ``default`` id as that same global
        fallback also keeps standalone/in-memory callers that omit a tenant
        argument reading the value they just saved, without sharing any
        non-default tenant bucket.
        """
        if spec.scope != "tenant":
            return None
        tenant_id = await resolve_tenant_id(request, default="default")
        return None if tenant_id == "default" else tenant_id

    @staticmethod
    def _settings_url(request: Request, namespace: str = "") -> str:
        """Build a settings URL under the request's configured admin mount."""
        return admin_url(
            admin_prefix_from_request(request),
            "settings",
            namespace,
        )

    @staticmethod
    def _history_url(request: Request, namespace: str) -> str:
        """Build the mount-aware settings history URL."""
        return admin_url(
            admin_prefix_from_request(request),
            "settings",
            f"history/{namespace}",
        )

    def _spec_ui_data(
        self,
        spec: type[Any],
        *,
        can_edit: bool | None = None,
        history_url: str | None = None,
    ) -> dict[str, Any]:
        """Return UI metadata with effective store and permission context."""
        data = spec.to_dict()
        data["store_name"] = self._store_name(spec)
        if can_edit is not None:
            data["can_edit"] = can_edit
        if history_url:
            data["history_url"] = history_url
        return data

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

    @staticmethod
    def _spec_permissions(spec: type[Any], operation: str) -> frozenset[str]:
        """Return the read/edit gate with legacy permission fallback."""
        configured = getattr(spec, f"{operation}_permissions", None)
        if configured is None:
            configured = getattr(spec, "required_permissions", frozenset())
        return frozenset(configured or ())

    def _can_access_spec(
        self,
        request: Request,
        spec: type[Any],
        operation: str,
    ) -> bool:
        """Check a spec's read or edit permission without trusting the UI."""
        required = self._spec_permissions(spec, operation)
        return (
            not required
            or self._user_is_superadmin(request)
            or self._user_permissions(request).issuperset(required)
        )

    def _build_categories(
        self, request: Request
    ) -> tuple[list[ConfigCategory], list[Any]]:
        """Build one category per package source, with visible specs for the user."""
        permissions = self._user_permissions(request)
        is_superadmin = self._user_is_superadmin(request)

        def _is_visible(spec: Any) -> bool:
            read_permissions = self._spec_permissions(spec, "read")
            return (
                not read_permissions
                or is_superadmin
                or permissions.issuperset(read_permissions)
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

    async def _panel_links(self, request: Request) -> list[PanelLink]:
        """Contributor settings-panel links for the sidebar (R50, doc 46).

        Panels (e.g. the core contributor's System Info page) live in the
        dashboard contributor catalog, not the ConfigRegistry — the sidebar
        renders the union. Permission filtering happens inside the
        assembler, keyed off the requesting user. Any failure degrades to a
        spec-only sidebar rather than breaking the Settings page.
        """
        if self._dashboard is None:
            return []
        try:
            user = getattr(getattr(request, "state", None), "user", None)
            admin_prefix = admin_prefix_from_request(request)
            panels = await self._dashboard.get_settings_panels(user)
            return [
                PanelLink(
                    title=panel.title,
                    url=mount_admin_url(panel.route_path, admin_prefix),
                    icon=getattr(panel, "icon", "") or "file-text",
                    category=getattr(panel, "category", "") or "Tools",
                )
                for panel in sorted(
                    panels,
                    key=lambda p: (getattr(p, "order", 100), p.title),
                )
                if getattr(panel, "route_path", "")
            ]
        except Exception:  # noqa: BLE001 — sidebar extras must never 500
            logger.warning("settings.panel_links_unavailable")
            return []

    def _get_csrf_token(self, request: Request) -> str | None:
        """Resolve the CSRF token for form rendering, if available."""
        if not self._csrf_service:
            return None
        try:
            session = getattr(request, "session", {})
            # Canonical session-id resolution — keep in sync with
            # middleware/csrf.py _validate_csrf and resources/handler.py.
            session_id: str = session.get("csrf_session_id") or session.get(
                "admin_user_id", "anonymous"
            )
            return self._csrf_service.generate_token(session_id)
        except Exception:  # noqa: BLE001 — non-fatal for form rendering
            logger.warning("settings.csrf_token_unavailable")
        return None

    @staticmethod
    def _safe_audit_value(value: Any, *, key: str | None = None) -> Any:
        """Keep audit values JSON-friendly without leaking credential material."""
        from lexigram.admin.settings.application import redact_config_value

        safe = redact_config_value(value, key=key)
        if safe is None or isinstance(safe, (bool, int, float, str)):
            return safe
        return str(safe)

    @classmethod
    def _non_secret_changes(
        cls,
        spec: type[Any],
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Build a non-secret before/after diff for settings audit records."""
        nodes = spec.get_nodes()
        changes: list[dict[str, Any]] = []
        for key in sorted(after):
            node = nodes.get(key)
            if node is None or isinstance(node, SecretNode):
                continue
            previous = before.get(key)
            current = after.get(key)
            if previous != current:
                changes.append(
                    {
                        "field": key,
                        "before": cls._safe_audit_value(previous, key=key),
                        "after": cls._safe_audit_value(current, key=key),
                    }
                )
        return changes

    @staticmethod
    def _settings_revision(spec: type[Any], values: dict[str, Any]) -> str:
        """Return a non-reversible revision token for the rendered settings."""
        return settings_revision(spec, values)

    @staticmethod
    def _revision_matches(
        expected: str | None,
        spec: type[Any],
        values: dict[str, Any],
    ) -> bool:
        """Compare a submitted revision without timing side channels.

        A missing token never matches: optimistic concurrency is mandatory on
        writes, so omitting the field cannot be used to bypass the check.
        """
        return revision_matches(expected, spec, values)

    async def _render_save_conflict(
        self,
        request: Request,
        spec: type[Any],
        namespace: str,
        tenant_id: str | None,
    ) -> Response:
        """Re-render the settings form showing current values after a conflict.

        Used both when the submitted revision is stale or missing and when a
        store rejects the write itself, so the two paths stay consistent. The
        form is rebuilt from freshly read values so the user reviews what is
        actually stored and receives a usable revision token.
        """
        conflict_message = (
            "These settings changed in another session. Review the current "
            "values before saving again."
        )
        current_values = await self._registry.get_values(
            namespace, self._store_name(spec), tenant_id=tenant_id
        )

        if request.headers.get("hx-request") == "true":
            self._flash_messages.clear()
            value_metadata = await self._registry.get_value_metadata(
                namespace,
                self._store_name(spec),
                tenant_id=tenant_id,
            )
            form_html = render_to_string(
                ConfigDashboardUI().render_config_form(
                    spec=self._spec_ui_data(
                        spec,
                        can_edit=True,
                        history_url=self._history_url(request, namespace),
                    ),
                    values=current_values,
                    errors={"__all__": conflict_message},
                    value_metadata=value_metadata,
                    revision=self._settings_revision(spec, current_values),
                    action=self._settings_url(request, namespace),
                    csrf_token=self._get_csrf_token(request),
                )
            )
            toast_html = self._render_toast(conflict_message, "warning")
            flash_oob = (
                f'<div id="flash-container" hx-swap-oob="true">{toast_html}</div>'
            )
            return HTMLResponse(flash_oob + form_html)

        return await self._render_spec_page(
            request,
            spec,
            current_values,
            errors={"__all__": conflict_message},
            status_code=409,
            tenant_id=tenant_id,
        )

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
                url=self._settings_url(request, visible[0].namespace),
                status_code=302,
            )

        layout = ConfigLayout(
            categories=categories,
            active_category=None,
            active_namespace=None,
            content=None,
            title="Settings",
            admin_prefix=admin_prefix_from_request(request),
            panel_links=await self._panel_links(request),
        )
        return await self.render_admin(
            request,
            layout,
            title="Settings",
            breadcrumbs=self.generate_breadcrumbs(
                ("Home", admin_url(admin_prefix_from_request(request), "")),
                current="Settings",
            ),
        )

    async def _render_spec_page(
        self,
        request: Request,
        spec: type[Any],
        values: dict[str, Any],
        errors: dict[str, str] | None = None,
        status_code: int = 200,
        tenant_id: str | None = None,
    ) -> Response:
        """Render a spec page, optionally preserving a failed submission."""
        categories, _ = self._build_categories(request)
        namespace = spec.namespace
        can_edit = self._can_access_spec(request, spec, "edit")
        effective_tenant_id = tenant_id
        if spec.scope == "tenant" and effective_tenant_id is None:
            effective_tenant_id = await self._tenant_for_spec(request, spec)
        value_metadata = await self._registry.get_value_metadata(
            namespace,
            self._store_name(spec),
            tenant_id=effective_tenant_id,
        )
        ui = ConfigDashboardUI()
        form_content = ui.render_config_form(
            spec=self._spec_ui_data(
                spec,
                can_edit=can_edit,
                history_url=self._history_url(request, namespace),
            ),
            values=values,
            errors=errors,
            value_metadata=value_metadata,
            revision=self._settings_revision(spec, values),
            action=self._settings_url(request, namespace),
            csrf_token=self._get_csrf_token(request),
        )

        layout = ConfigLayout(
            categories=categories,
            active_category=spec.package_source,
            active_namespace=namespace,
            content=form_content,
            title="Settings",
            admin_prefix=admin_prefix_from_request(request),
            panel_links=await self._panel_links(request),
        )

        if request.headers.get("hx-request") == "true" and request.headers.get(
            "hx-target"
        ) in {"#settings-content", "settings-content"}:
            response = HTMLResponse(
                render_to_string(form_content), status_code=status_code
            )
        else:
            response = await self.render_admin(
                request,
                layout,
                title=f"{spec.label or namespace} - Settings",
                breadcrumbs=self.generate_breadcrumbs(
                    ("Home", admin_url(admin_prefix_from_request(request), "")),
                    ("Settings", self._settings_url(request)),
                    current=spec.label or namespace,
                ),
            )
            response.status_code = status_code
        return response

    async def _render_history_content(
        self,
        request: Request,
        spec: type[Any],
        namespace: str,
        tenant_id: str | None,
        snapshots: list[Any],
        current_values: dict[str, Any],
    ) -> Any:
        """Render the history list and safe rollback forms."""
        can_edit = self._can_access_spec(request, spec, "edit")
        current_revision = self._settings_revision(spec, current_values)
        children: list[Any] = [
            el(
                "a",
                "← Back to settings",
                href=self._settings_url(request, namespace),
                hx_get=self._settings_url(request, namespace),
                hx_target="#settings-content",
                hx_swap="innerHTML",
                hx_push_url="true",
                data_admin_navigation=True,
                class_="inline-flex text-sm font-medium text-primary-700 underline-offset-4 hover:underline dark:text-primary-400",
            ),
            el(
                "div",
                el(
                    "h2",
                    "Change history",
                    class_="text-xl font-semibold text-foreground",
                ),
                el(
                    "p",
                    "Snapshots contain non-secret values from immediately before a successful change. Failed or stale saves are never recorded.",
                    class_="mt-1 text-sm text-muted-foreground",
                ),
                class_="mt-5 mb-5",
            ),
        ]
        if not snapshots:
            children.append(
                el(
                    "div",
                    "No changes have been recorded for this namespace.",
                    role="status",
                    class_="rounded-lg border border-border bg-muted px-4 py-6 text-sm text-muted-foreground",
                )
            )

        csrf_token = self._get_csrf_token(request)
        for snapshot in snapshots:
            value_text = (
                "\n".join(
                    f"{key}: {value!s}"
                    for key, value in sorted(snapshot.values.items())
                )
                or "No non-secret fields captured."
            )
            snapshot_children: list[Any] = [
                el(
                    "div",
                    el(
                        "strong",
                        snapshot.created_at.isoformat(),
                        class_="text-sm font-medium text-foreground",
                    ),
                    el(
                        "span",
                        f" · by {snapshot.actor_id} · {snapshot.comment or 'save'}",
                        class_="text-xs text-muted-foreground",
                    ),
                    class_="flex flex-wrap items-baseline gap-1",
                ),
                el(
                    "pre",
                    value_text,
                    tabindex="0",
                    class_="mt-3 max-h-64 overflow-auto rounded-md bg-muted p-3 text-xs text-foreground whitespace-pre-wrap",
                ),
            ]
            if snapshot.skipped_secrets:
                snapshot_children.append(
                    el(
                        "p",
                        "Secret fields were intentionally excluded: ",
                        el(
                            "span",
                            ", ".join(snapshot.skipped_secrets),
                            class_="font-medium",
                        ),
                        class_="mt-2 text-xs text-muted-foreground",
                    )
                )
            if snapshot.unset_keys:
                snapshot_children.append(
                    el(
                        "p",
                        "Inherited defaults will be restored for: ",
                        el(
                            "span",
                            ", ".join(snapshot.unset_keys),
                            class_="font-medium",
                        ),
                        class_="mt-2 text-xs text-muted-foreground",
                    )
                )
            if can_edit and (snapshot.values or snapshot.unset_keys):
                hidden = [
                    el(
                        "input",
                        type="hidden",
                        name="rollback_to",
                        value=snapshot.snapshot_id,
                    ),
                    el(
                        "input",
                        type="hidden",
                        name="settings_revision",
                        value=current_revision,
                    ),
                ]
                if csrf_token:
                    hidden.insert(
                        0,
                        el("input", type="hidden", name="csrf_token", value=csrf_token),
                    )
                snapshot_children.append(
                    el(
                        "form",
                        *hidden,
                        el(
                            "button",
                            "Restore this snapshot",
                            type="submit",
                            class_="mt-3 inline-flex items-center rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-foreground shadow-sm hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                        ),
                        action=self._settings_url(request, namespace),
                        method="post",
                        hx_post=self._settings_url(request, namespace),
                        hx_target="#settings-content",
                        hx_swap="innerHTML",
                        data_admin_form=True,
                        data_settings_rollback=True,
                    )
                )
            children.append(
                el(
                    "article",
                    *snapshot_children,
                    class_="rounded-lg border border-border bg-card p-4 shadow-sm",
                    data_snapshot_id=snapshot.snapshot_id,
                )
            )

        return el("div", *children, class_="space-y-4")

    @get("/history/{namespace:path}")
    async def history(self, request: Request) -> Response:
        """Show safe namespace history and restore actions."""
        namespace = request.path_params.get("namespace", "")
        spec = self._registry.get_spec(namespace)
        if not spec or not spec.get_nodes():
            self.flash(f"Configuration '{namespace}' not found.", "error")
            return RedirectResponse(url=self._settings_url(request), status_code=302)
        if not self._can_access_spec(request, spec, "read"):
            await self._audit(
                request,
                success=False,
                event_type=AdminSecurityEventType.PERMISSION_DENIED,
                namespace=namespace,
                reason="permission_denied",
            )
            self.flash("You do not have permission to view this setting.", "error")
            return RedirectResponse(url=self._settings_url(request), status_code=302)

        tenant_id = await self._tenant_for_spec(request, spec)
        current_values = await self._registry.get_values(
            namespace, self._store_name(spec), tenant_id=tenant_id
        )
        try:
            snapshots = await self._snapshots.list_history(namespace, tenant_id)
        except Exception:  # noqa: BLE001 — history must not break settings access
            logger.warning("settings.history_unavailable", namespace=namespace)
            snapshots = []

        content = await self._render_history_content(
            request,
            spec,
            namespace,
            tenant_id,
            snapshots,
            current_values,
        )
        if request.headers.get("hx-request") == "true":
            return HTMLResponse(render_to_string(content))

        categories, _ = self._build_categories(request)
        layout = ConfigLayout(
            categories=categories,
            active_category=spec.package_source,
            active_namespace=namespace,
            content=content,
            title="Settings",
            admin_prefix=admin_prefix_from_request(request),
            panel_links=await self._panel_links(request),
        )
        return await self.render_admin(
            request,
            layout,
            title=f"{spec.label or namespace} - History",
            breadcrumbs=self.generate_breadcrumbs(
                ("Home", admin_url(admin_prefix_from_request(request), "")),
                ("Settings", self._settings_url(request)),
                (spec.label or namespace, self._settings_url(request, namespace)),
                current="History",
            ),
        )

    @get("/{namespace:path}")
    async def spec_view(self, request: Request) -> Response:
        """Spec detail/edit view."""
        namespace = request.path_params.get("namespace", "")
        spec = self._registry.get_spec(namespace)
        if not spec or not spec.get_nodes():
            self.flash(f"Configuration '{namespace}' not found.", "error")
            return RedirectResponse(url=self._settings_url(request), status_code=302)

        if not self._can_access_spec(request, spec, "read"):
            await self._audit(
                request,
                success=False,
                event_type=AdminSecurityEventType.PERMISSION_DENIED,
                reason="permission_denied",
            )
            self.flash("You do not have permission to view this setting.", "error")
            return RedirectResponse(url=self._settings_url(request), status_code=302)

        tenant_id = await self._tenant_for_spec(request, spec)
        values = await self._registry.get_values(
            namespace, self._store_name(spec), tenant_id=tenant_id
        )
        return await self._render_spec_page(
            request,
            spec,
            values,
            tenant_id=tenant_id,
        )

    @post("/{namespace:path}")
    async def save_spec(self, request: Request) -> Response:
        """Save configuration changes for a spec."""
        namespace = request.path_params.get("namespace", "")
        spec = self._registry.get_spec(namespace)
        if not spec or not spec.get_nodes():
            self.flash(f"Configuration '{namespace}' not found.", "error")
            return RedirectResponse(url=self._settings_url(request), status_code=302)

        if not self._can_access_spec(request, spec, "edit"):
            await self._audit(
                request,
                success=False,
                event_type=AdminSecurityEventType.PERMISSION_DENIED,
                reason="permission_denied",
            )
            self.flash("You do not have permission to edit this setting.", "error")
            return RedirectResponse(
                url=self._settings_url(request, namespace),
                status_code=302,
            )

        form = request.scope.get("admin_form_data")
        if form is None:
            form = await request.form()

        nodes = spec.get_nodes()
        multi = getattr(form, "multi_items", None)
        raw_items = list(multi()) if multi else list(form.items())
        raw_values: dict[str, list[Any]] = {}
        for key, value in raw_items:
            if not key.startswith("_") and key in nodes:
                raw_values.setdefault(key, []).append(value)

        # Checkboxes submit both a checked value and a hidden false fallback.
        # Resolve all values explicitly instead of relying on dict ordering,
        # which previously made a checked toggle save as false.
        updates: dict[str, Any] = {}
        for key, submitted in raw_values.items():
            if isinstance(nodes[key], BooleanNode):
                normalized = [str(value).strip().lower() for value in submitted]
                if any(value in BooleanNode.TRUE_VALUES for value in normalized):
                    updates[key] = "true"
                elif all(value in BooleanNode.FALSE_VALUES for value in normalized):
                    updates[key] = "false"
                else:
                    updates[key] = submitted[-1]
            else:
                updates[key] = submitted[-1]

        ignored_readonly = sorted(key for key in updates if nodes[key].readonly)
        editable_updates = {
            key: value for key, value in updates.items() if not nodes[key].readonly
        }
        tenant_id = await self._tenant_for_spec(request, spec)
        existing_values = await self._registry.get_values(
            namespace, self._store_name(spec), tenant_id=tenant_id
        )
        existing_metadata = await self._registry.get_value_metadata(
            namespace,
            self._store_name(spec),
            tenant_id=tenant_id,
        )

        # A rollback submission replaces the posted values with a stored
        # snapshot and then continues down the ordinary save path, so it is
        # subject to the same validation, concurrency, and audit rules.
        rollback = await self._resolve_rollback(form, spec, namespace, tenant_id)
        rollback_getter = getattr(form, "get", None)
        rollback_id = (
            str(rollback_getter("rollback_to") or "")
            if callable(rollback_getter)
            else ""
        )
        # A hidden rollback form has no ordinary field values. If its opaque
        # id is missing, expired, or belongs to another scope, do not let it
        # fall through as a normal save (which would synthesize unchecked
        # booleans as false). Preserve the legacy mixed-form behavior when a
        # caller deliberately supplies an ordinary editable value as well.
        if rollback_id and rollback is None and not editable_updates:
            await self._audit(
                request,
                success=False,
                namespace=namespace,
                reason="rollback_unavailable",
            )
            self.flash("That settings snapshot is no longer available.", "error")
            return RedirectResponse(
                url=self._settings_url(request, namespace),
                status_code=302,
            )

        is_rollback = rollback is not None
        rollback_unset_keys: set[str] = set()
        if rollback is not None:
            editable_updates = dict(rollback.values)
            updates = dict(rollback.values)
            rollback_unset_keys = set(rollback.unset_keys)
            ignored_readonly = []

        # Optimistic concurrency is mandatory: a submission that omits the
        # token is rejected exactly like a stale one, so dropping the field
        # cannot bypass the check.
        submitted_revision = extract_submitted_revision(form)
        if not self._revision_matches(submitted_revision, spec, existing_values):
            await self._audit(
                request,
                success=False,
                namespace=namespace,
                reason=(
                    "concurrent_update"
                    if submitted_revision
                    else "missing_settings_revision"
                ),
            )
            return await self._render_save_conflict(request, spec, namespace, tenant_id)

        # Missing unchecked checkboxes are equivalent to false even when a
        # client omits the hidden fallback. Required non-boolean fields are
        # reported rather than silently omitted.
        validation_errors: dict[str, str] = {}
        for key, node in nodes.items():
            if node.readonly or key in editable_updates:
                continue
            if isinstance(node, BooleanNode):
                editable_updates[key] = "false"
            elif node.required:
                validation_errors[key] = node.validation_error("") or (
                    f"{node.label} is required."
                )

        preserved_secrets: list[str] = []
        for key in list(editable_updates):
            node = nodes[key]
            if isinstance(node, SecretNode) and not str(editable_updates[key]):
                if node.required and not existing_values.get(key):
                    validation_errors[key] = node.validation_error("") or (
                        f"{node.label} is required."
                    )
                else:
                    editable_updates.pop(key)
                    preserved_secrets.append(key)

        validated_updates: dict[str, Any] = {}
        for key, value in editable_updates.items():
            error = nodes[key].validation_error(value)
            if error:
                validation_errors[key] = error
            else:
                validated_updates[key] = nodes[key].validate(value)

        # Do not turn a form that merely re-submits its current values into a
        # history entry or an unnecessary database write. Equality is checked
        # after node coercion, so "60" and 60 are the same effective value.
        validated_updates = {
            key: value
            for key, value in validated_updates.items()
            if key not in rollback_unset_keys
            and (
                existing_values.get(key) != value
                or (
                    is_rollback
                    and existing_metadata.get(key, {}).get("configured") is not True
                )
            )
        }
        delete_keys = {
            key
            for key in rollback_unset_keys
            if existing_metadata.get(key, {}).get("configured") is True
        }

        # Start from the effective values and overlay the submitted values so
        # an invalid form can be re-rendered without losing the user's input.
        display_values = dict(existing_values)
        for key, value in updates.items():
            if key in nodes and not nodes[key].readonly:
                display_values[key] = (
                    nodes[key].validate(value)
                    if isinstance(nodes[key], BooleanNode)
                    else value
                )
        for key in editable_updates:
            if isinstance(nodes[key], SecretNode):
                # Never echo a submitted secret back into HTML.
                display_values[key] = existing_values.get(key, "")

        if validation_errors:
            await self._audit(
                request,
                success=False,
                namespace=namespace,
                keys=[],
                invalid=sorted(validation_errors),
                validation_errors=sorted(validation_errors),
                ignored_readonly=ignored_readonly,
                preserved_secrets=sorted(preserved_secrets),
                # Keep the legacy audit key for downstream consumers; blank
                # secret fields have always meant "preserve", not delete.
                cleared_secrets=sorted(preserved_secrets),
            )
            ui = ConfigDashboardUI()
            value_metadata = await self._registry.get_value_metadata(
                namespace,
                self._store_name(spec),
                tenant_id=tenant_id,
            )
            form_html = render_to_string(
                ui.render_config_form(
                    spec=self._spec_ui_data(
                        spec,
                        can_edit=True,
                        history_url=self._history_url(request, namespace),
                    ),
                    values=display_values,
                    errors=validation_errors,
                    value_metadata=value_metadata,
                    revision=self._settings_revision(spec, existing_values),
                    action=self._settings_url(request, namespace),
                    csrf_token=self._get_csrf_token(request),
                )
            )
            if request.headers.get("hx-request") == "true":
                self._flash_messages.clear()
                toast_html = self._render_toast(
                    f"No changes saved. Fix {len(validation_errors)} field error(s).",
                    "warning",
                )
                flash_oob = (
                    f'<div id="flash-container" hx-swap-oob="true">{toast_html}</div>'
                )
                # Keep this response 200 so HTMX swaps the form. Its
                # default response policy deliberately does not swap 4xx
                # responses, while this fragment contains the recoverable
                # field-level errors the user needs to see.
                return HTMLResponse(flash_oob + form_html)

            return await self._render_spec_page(
                request,
                spec,
                display_values,
                errors=validation_errors,
                status_code=422,
                tenant_id=tenant_id,
            )

        wrote_values = bool(validated_updates or delete_keys)
        if wrote_values:
            # The revision comparison above happened before this write, so a
            # save committed in between would otherwise be silently
            # overwritten. Pass the values the form was rendered from so
            # stores that support it can re-check inside the write transaction
            # and reject a late conflict.
            try:
                await self._registry.save_values(
                    namespace,
                    validated_updates,
                    self._store_name(spec),
                    tenant_id=tenant_id,
                    expected={
                        key: existing_values[key]
                        for key in set(validated_updates).union(delete_keys)
                        if key in existing_values
                    },
                    delete_keys=delete_keys,
                )
            except SettingsConflictError:
                await self._audit(
                    request,
                    success=False,
                    namespace=namespace,
                    reason="concurrent_update_at_write",
                    keys=sorted(validated_updates),
                )
                return await self._render_save_conflict(
                    request, spec, namespace, tenant_id
                )

            # Capture only after the conditional write succeeds. A snapshot
            # taken before the write survives a lost race and falsely suggests
            # that a failed save can be rolled back.
            await self._capture_snapshot(
                request,
                spec,
                namespace,
                existing_values,
                tenant_id,
                comment="rollback" if is_rollback else "save",
                unset_keys={
                    key
                    for key, metadata in existing_metadata.items()
                    if metadata.get("configured") is False
                },
            )

        effective_after = dict(existing_values)
        effective_after.update(validated_updates)
        for key in delete_keys:
            effective_after[key] = nodes[key].default
        await self._audit(
            request,
            namespace=namespace,
            keys=sorted(set(validated_updates).union(delete_keys)),
            changes=self._non_secret_changes(spec, existing_values, effective_after),
            invalid=[],
            ignored_readonly=ignored_readonly,
            preserved_secrets=sorted(preserved_secrets),
            cleared_secrets=sorted(preserved_secrets),
            unset_keys=sorted(delete_keys),
            rollback=is_rollback,
            no_op=not wrote_values,
        )

        if request.headers.get("hx-request") == "true":
            self._flash_messages.clear()
            message = (
                "No changes were needed."
                if not wrote_values
                else "Settings saved successfully."
            )
            if ignored_readonly:
                message += " Read-only fields were ignored."
            if preserved_secrets:
                message += " Existing secrets were kept."
            toast_html = self._render_toast(message, "success")
            flash_oob = (
                f'<div id="flash-container" hx-swap-oob="true">{toast_html}</div>'
            )

            values = await self._registry.get_values(
                namespace, self._store_name(spec), tenant_id=tenant_id
            )
            ui = ConfigDashboardUI()
            value_metadata = await self._registry.get_value_metadata(
                namespace,
                self._store_name(spec),
                tenant_id=tenant_id,
            )
            form_content = ui.render_config_form(
                spec=self._spec_ui_data(
                    spec,
                    can_edit=True,
                    history_url=self._history_url(request, namespace),
                ),
                values=values,
                value_metadata=value_metadata,
                revision=self._settings_revision(spec, values),
                action=self._settings_url(request, namespace),
                csrf_token=self._get_csrf_token(request),
            )
            form_html = render_to_string(form_content)

            return HTMLResponse(flash_oob + form_html)

        self.flash(
            "No changes were needed."
            if not wrote_values
            else "Settings saved successfully.",
            "success",
        )
        return RedirectResponse(
            url=self._settings_url(request, namespace),
            status_code=302,
        )

    def _render_toast(self, message: str, kind: str) -> str:
        """Build a visible, accessible toast for HTMX responses."""
        rendered = ServerToastChannel().render_toast(
            ToastData(message=message, type=kind)
        )
        # Keep the long-standing exact ``class="toast toast-{kind}"``
        # contract for consumers that style or assert it. The shared renderer
        # starts animated toasts with ``show``; the HTMX fragment is already
        # mounted, so make this server-delivered toast visible immediately
        # without requiring a second client lifecycle pass.
        color = {
            "success": "green",
            "error": "red",
            "warning": "yellow",
            "info": "blue",
        }.get(kind, "blue")
        rendered = rendered.replace(
            f'class="toast toast-{kind} toast-{color} show"',
            f'class="toast toast-{kind}" style="transform: translateX(0); opacity: 1"',
            1,
        )
        # The message is in a text node, not an attribute. Keep the legacy
        # text-node escaping contract where quotes remain readable while
        # angle brackets stay escaped and therefore cannot become markup.
        return rendered.replace("&#34;", '"').replace("&#39;", "'")
