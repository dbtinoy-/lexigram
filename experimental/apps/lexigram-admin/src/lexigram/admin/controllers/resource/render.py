"""Form rendering for the resource controller."""

from __future__ import annotations

from collections.abc import Mapping
from html import escape
from typing import Any

from lexigram.admin.controllers.resource.meta import ResourceMeta, T
from lexigram.admin.resources.urls import admin_prefix_from_request, admin_url
from lexigram.admin.state.context import AdminContext


class ResourceRenderMixin:
    """Form rendering hooks."""

    # Host attributes provided by sibling mixins on ResourceController.
    meta: ResourceMeta

    def render_form(
        self,
        ctx: AdminContext,
        item: T | None,
        data: dict[str, Any] | None = None,
        errors: dict[str, list[str]] | None = None,
    ) -> str:
        """Render a compatibility form page.

        Resource subclasses should provide their own renderer (the active
        resource pipeline does this through ``FormRenderer``). The fallback is
        nevertheless a real, progressively enhanced form so an older
        controller cannot silently emit an unusable or unprotected POST
        surface while an integration is being migrated.
        """
        title = f"Edit {self.meta.label}" if item else f"Create {self.meta.label}"
        safe_title = escape(title)
        return f"""
<!DOCTYPE html>
<html>
<head><title>{safe_title}</title></head>
<body>
    <h1>{safe_title}</h1>
    {self.render_form_partial(ctx, item, data, errors)}
</body>
</html>
"""

    def render_form_partial(
        self,
        ctx: AdminContext,
        item: T | None,
        data: dict[str, Any] | None = None,
        errors: dict[str, list[str]] | None = None,
    ) -> str:
        """Render form content. Override in subclass."""
        request = ctx.request
        scope = getattr(request, "scope", None)
        scope_prefix = scope.get("admin_prefix") if isinstance(scope, Mapping) else None
        app_prefix = getattr(
            getattr(getattr(request, "app", None), "state", None),
            "admin_prefix",
            None,
        )
        configured_prefix = getattr(self.meta, "prefix", "")
        prefix = (
            scope_prefix.rstrip("/")
            if isinstance(scope_prefix, str) and scope_prefix
            else (
                admin_prefix_from_request(request)
                if isinstance(app_prefix, str) and app_prefix
                else (configured_prefix or "").rstrip("/")
                or admin_prefix_from_request(request)
            )
        )
        action = admin_url(prefix, self.meta.name)
        if item:
            id_val = (
                item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
            )
            if id_val is not None:
                action = admin_url(prefix, self.meta.name, str(id_val))

        request_state = getattr(request, "state", None)
        csrf_token = getattr(request_state, "csrf_token", None)
        csrf_input = (
            f'<input type="hidden" name="csrf_token" value="{escape(str(csrf_token), quote=True)}">'
            if csrf_token
            else ""
        )

        error_items: list[str] = []
        for field, messages in (errors or {}).items():
            normalized = messages if isinstance(messages, list) else [messages]
            for message in normalized:
                error_items.append(
                    f'<li><strong>{escape(str(field))}:</strong> '
                    f"{escape(str(message))}</li>"
                )
        error_block = (
            '<div role="alert" class="resource-form-errors">'
            '<p>Check the form and try again.</p><ul>'
            + "".join(error_items)
            + "</ul></div>"
            if error_items
            else ""
        )

        htmx_attrs = ""
        if ctx.is_htmx:
            target = request.headers.get("HX-Target") or "#main-content"
            htmx_attrs = (
                f' hx-post="{escape(action, quote=True)}"'
                f' hx-target="{escape(target, quote=True)}" hx-swap="innerHTML"'
            )

        safe_action = escape(action, quote=True)
        resource_name = escape(str(self.meta.name), quote=True)
        return f"""
<form method="POST" action="{safe_action}" data-admin-form="true"
      data-resource-form="{resource_name}" aria-busy="false"{htmx_attrs}>
    {csrf_input}
    <p data-admin-form-status="true" aria-live="polite" class="sr-only"></p>
    {error_block}
    <p role="status">This compatibility form has no generated fields. Override
       render_form_partial() to provide the resource fields.</p>
    <div data-admin-form-actions="true">
        <button type="submit">Save</button>
    </div>
</form>
"""
