"""Form rendering for the resource controller."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.controllers.resource.meta import T
from lexigram.admin.data.data_source import QueryResult
from lexigram.admin.state.context import AdminContext
from lexigram.admin.state.url import URLState
from lexigram.ui import el, render_to_string

if TYPE_CHECKING:
    from lexigram.admin.controllers.resource import ResourceController



class ResourceRenderMixin:
    """Form rendering hooks."""

    def render_form(self: ResourceController,
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

    def render_form_partial(self: ResourceController,
        ctx: AdminContext,
        item: T | None,
        data: dict[str, Any] | None = None,
        errors: dict[str, list[str]] | None = None,
    ) -> str:
        """Render form content. Override in subclass."""
        action = f"{self.meta.prefix}/{self.meta.name}"
        if item:
            id_val = getattr(item, "id", None)
            action = f"{action}/{id_val}"

        return f"""
<form method="POST" action="{action}">
    <p>Override render_form_partial() to customize</p>
    <button type="submit">Save</button>
</form>
"""
