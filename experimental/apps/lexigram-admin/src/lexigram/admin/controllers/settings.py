"""Spec-driven settings controller for the admin interface.

Renders editable configuration specs (branding, caching, security) through
the config panel UI and persists values to the DB-backed store.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.config import AdminRbacConfig
from lexigram.admin.controllers.base import AdminController
from lexigram.admin.multitenancy.adapter import resolve_tenant_id
from lexigram.admin.rbac.super_admin import is_super_admin
from lexigram.admin.resources.urls import admin_prefix_from_request, admin_url
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
        return (
            spec.store_name if self._registry.has_store(spec.store_name) else "default"
        )

    @staticmethod
    def _settings_url(request: Request, namespace: str = "") -> str:
        """Build a settings URL under the request's configured admin mount."""
        return admin_url(
            admin_prefix_from_request(request),
            "settings",
            namespace,
        )

    def _spec_ui_data(
        self,
        spec: type[Any],
        *,
        can_edit: bool | None = None,
    ) -> dict[str, Any]:
        """Return UI metadata with effective store and permission context."""
        data = spec.to_dict()
        data["store_name"] = self._store_name(spec)
        if can_edit is not None:
            data["can_edit"] = can_edit
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
    def _safe_audit_value(value: Any) -> Any:
        """Keep audit values JSON-friendly without leaking object internals."""
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        return str(value)

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
                        "before": cls._safe_audit_value(previous),
                        "after": cls._safe_audit_value(current),
                    }
                )
        return changes

    @staticmethod
    def _settings_revision(spec: type[Any], values: dict[str, Any]) -> str:
        """Return a non-reversible revision token for the rendered settings."""
        revision_values: list[tuple[str, Any]] = []
        for key, node in sorted(spec.get_nodes().items()):
            value = values.get(key)
            # Include only whether a secret is present. Hashing its content
            # would still create an unnecessary secret-derived identifier.
            if isinstance(node, SecretNode):
                value = "<set>" if value else "<unset>"
            revision_values.append((key, value))
        payload = json.dumps(
            revision_values,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _revision_matches(
        expected: str | None,
        spec: type[Any],
        values: dict[str, Any],
    ) -> bool:
        """Compare a submitted revision without timing side channels."""
        return not expected or hmac.compare_digest(
            expected,
            SettingsController._settings_revision(spec, values),
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
            effective_tenant_id = await resolve_tenant_id(request, default="default")
        value_metadata = await self._registry.get_value_metadata(
            namespace,
            self._store_name(spec),
            tenant_id=effective_tenant_id,
        )
        ui = ConfigDashboardUI()
        form_content = ui.render_config_form(
            spec=self._spec_ui_data(spec, can_edit=can_edit),
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
        )

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

        tenant_id = (
            await resolve_tenant_id(request, default="default")
            if spec.scope == "tenant"
            else None
        )
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
        tenant_id = (
            await resolve_tenant_id(request, default="default")
            if spec.scope == "tenant"
            else None
        )
        existing_values = await self._registry.get_values(
            namespace, self._store_name(spec), tenant_id=tenant_id
        )

        submitted_revision = form.get("settings_revision")
        if submitted_revision and not self._revision_matches(
            str(submitted_revision), spec, existing_values
        ):
            await self._audit(
                request,
                success=False,
                namespace=namespace,
                reason="concurrent_update",
            )
            conflict_message = (
                "These settings changed in another session. Review the current "
                "values before saving again."
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
                        spec=self._spec_ui_data(spec, can_edit=True),
                        values=existing_values,
                        errors={"__all__": conflict_message},
                        value_metadata=value_metadata,
                        revision=self._settings_revision(spec, existing_values),
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
                existing_values,
                errors={"__all__": conflict_message},
                status_code=409,
                tenant_id=tenant_id,
            )

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
                    spec=self._spec_ui_data(spec, can_edit=True),
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

        await self._registry.save_values(
            namespace,
            validated_updates,
            self._store_name(spec),
            tenant_id=tenant_id,
        )

        await self._audit(
            request,
            namespace=namespace,
            keys=sorted(validated_updates),
            changes=self._non_secret_changes(spec, existing_values, validated_updates),
            invalid=[],
            ignored_readonly=ignored_readonly,
            preserved_secrets=sorted(preserved_secrets),
            cleared_secrets=sorted(preserved_secrets),
        )

        if request.headers.get("hx-request") == "true":
            self._flash_messages.clear()
            message = "Settings saved successfully."
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
                spec=self._spec_ui_data(spec, can_edit=True),
                values=values,
                value_metadata=value_metadata,
                revision=self._settings_revision(spec, values),
                action=self._settings_url(request, namespace),
                csrf_token=self._get_csrf_token(request),
            )
            form_html = render_to_string(form_content)

            return HTMLResponse(flash_oob + form_html)

        self.flash("Settings saved successfully.", "success")
        return RedirectResponse(
            url=self._settings_url(request, namespace),
            status_code=302,
        )

    def _render_toast(self, message: str, kind: str) -> str:
        """Build a toast component for htmx responses."""
        return render_to_string(el("div", {"class": f"toast toast-{kind}"}, message))
