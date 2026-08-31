"""Form rendering for the resource controller."""

from __future__ import annotations

from collections.abc import Mapping
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
        """Render full form page. Override in subclass."""
        title = f"Edit {self.meta.label}" if item else f"Create {self.meta.label}"
        return f"""
<!DOCTYPE html>
<html>
<head><title>{title}</title></head>
<body>
    <h1>{title}</h1>
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
        configured_prefix = getattr(self.meta, "prefix", "")
        prefix = (
            scope_prefix.rstrip("/")
            if isinstance(scope_prefix, str) and scope_prefix
            else (
                (configured_prefix or "").rstrip("/")
                or admin_prefix_from_request(request)
            )
        )
        action = admin_url(prefix, self.meta.name)
        if item:
            id_val = (
                item.get("id")
                if isinstance(item, dict)
                else getattr(item, "id", None)
            )
            if id_val is not None:
                action = admin_url(prefix, self.meta.name, str(id_val))

        from html import escape

        action = escape(action, quote=True)
        return f"""
<form method="POST" action="{action}">
    <p>Override render_form_partial() to customize</p>
    <button type="submit">Save</button>
</form>
"""
