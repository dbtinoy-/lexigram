"""Detail view for the resource controller."""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

from lexigram.admin.controllers.resource.meta import T
from lexigram.admin.data.data_source import IDataSource as DataSourceProtocol
from lexigram.admin.state.context import AdminContext, AdminContextManager
from lexigram.ui import el, render_to_string

if TYPE_CHECKING:
    from lexigram.admin.controllers.resource import ResourceController



class ResourceDetailMixin:
    """Detail view and rendering."""

    async def detail(self: ResourceController, request: Request) -> Response:
        """View single resource."""
        async with AdminContextManager(request) as ctx:
            item_id = request.path_params.get("id")

            data_source = self.get_data_source()
            item = await data_source.find_one(item_id)

            if item is None:
                from lexigram.admin.lib.template import render_error_page

                html = render_error_page(
                    status_code=404,
                    title="Not Found",
                    message=f"{self.meta.label} not found",
                )
                return HTMLResponse(html, status_code=404)

            if ctx.is_htmx:
                return HTMLResponse(self.render_detail_partial(ctx, item))

            return HTMLResponse(self.render_detail(ctx, item))
    def render_detail(self: ResourceController, ctx: AdminContext, item: T) -> str:
        """Render full detail page. Override in subclass."""
        return f"""
<!DOCTYPE html>
<html>
<head><title>{self.meta.label}</title></head>
<body>
    <h1>{self.meta.label}</h1>
    {self.render_detail_partial(ctx, item)}
</body>
</html>
"""

    def render_detail_partial(self: ResourceController, ctx: AdminContext, item: T) -> str:
        """Render detail content. Override in subclass."""
        return render_to_string(el("pre", str(item)))
