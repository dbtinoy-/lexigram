from __future__ import annotations

"""Detail view rendering for admin resources."""

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.admin.config import AdminConfig
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.exceptions import DataError
from lexigram.admin.observability.admin_metrics import AdminMetrics, OperationTimer
from lexigram.admin.state.context import wants_fragment
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.ui import el, render_to_string

logger = get_logger(__name__)


@inject
class DetailRenderer:
    """Handles rendering of detail views for admin resources."""

    def __init__(
        self,
        config: AdminConfig,
        resource_name: str,
        renderer: AdminRenderer,
        metrics: AdminMetrics | None = None,
    ):
        self._config = config
        self.resource_name = resource_name
        self._renderer = renderer
        self._metrics = metrics or AdminMetrics(None)

    async def render_detail(
        self,
        request,
        resource,
        item_id: str,
        user=None,
    ) -> HTMLResponse:
        """Render detail view."""
        timer = OperationTimer()

        label = self.resource_name.replace("_", " ").title()

        item_html = await self._get_item_html(resource, item_id, label)

        content = f"""
        <div class="resource-header" style="margin-bottom: 1.5rem;">
            <a href="{self._config.prefix}/{self.resource_name}" style="color: #6366f1;">&larr; Back to {label}</a>
            <h1>{label} #{item_id}</h1>
        </div>
        <div class="resource-content">{item_html}</div>
        <div class="resource-actions" style="margin-top: 1rem;">
            <a href="{self._config.prefix}/{self.resource_name}/{item_id}/edit" class="btn btn-secondary">Edit</a>
        </div>
        """

        is_htmx = wants_fragment(request)
        if is_htmx:
            self._metrics.record_operation(
                "detail",
                resource=self.resource_name,
                status="success",
                duration_seconds=timer.elapsed(),
            )
            return HTMLResponse(content)

        self._metrics.record_operation(
            "detail",
            resource=self.resource_name,
            status="success",
            duration_seconds=timer.elapsed(),
        )

        return self._renderer.render_page(
            content,
            request=request,
            title=f"{label} #{item_id}",
            breadcrumbs=[
                {"label": "Dashboard", "url": self._config.prefix},
                {"label": label, "url": f"{self._config.prefix}/{self.resource_name}"},
                {
                    "label": f"#{item_id}",
                    "url": f"{self._config.prefix}/{self.resource_name}/{item_id}",
                },
            ],
        )

    async def render_inline_edit(
        self,
        request,
        resource,
        item_id: str,
        user=None,
    ) -> HTMLResponse:
        """Render detail view with inline editable fields.

        Each field is rendered as an Alpine.js-driven inline editor.  In
        *display* mode the current value is shown with a pencil icon that
        appears on hover.  Clicking the icon switches to *edit* mode which
        shows an ``<input>`` alongside Save and Cancel buttons.  Saving
        issues an HTMX ``PATCH`` to
        ``/{resource_name}/{item_id}/inline?field=<name>`` carrying the new
        value.

        Args:
            request: Incoming HTTP request.
            resource: Admin resource instance.
            item_id: Primary-key value of the record to display.
            user: Authenticated user (optional, for future RBAC use).

        Returns:
            ``HTMLResponse`` with the inline-edit fragment or full page.
        """
        label = self.resource_name.replace("_", " ").title()
        item_dict: dict = {}

        if resource and hasattr(resource, "service") and resource.service:
            try:
                if hasattr(resource.service, "get"):
                    item = await resource.service.get(item_id)
                    if item:
                        item_dict = (
                            item.model_dump()
                            if hasattr(item, "model_dump")
                            else dict(item)
                        )
            except DataError as exc:
                logger.debug(
                    "inline_edit fetch failed resource=%s id=%s: %s",
                    self.resource_name,
                    item_id,
                    exc,
                )
                raise DataError(
                    message=f"Failed to retrieve {self.resource_name} item {item_id}",
                    original_error=exc,
                ) from None

        patch_base = f"{self._config.prefix}/{self.resource_name}/{item_id}/inline"

        field_rows: list[Any] = []
        for field_name, field_value in item_dict.items():
            alpine_key = f"editing_{field_name}"
            row = el(
                "tr",
                el(
                    "td",
                    el("strong", field_name),
                    class_="py-2 pr-4 align-top text-sm font-medium text-muted-foreground w-1/4",
                ),
                el(
                    "td",
                    # Display mode
                    el(
                        "div",
                        el(
                            "span",
                            str(field_value),
                            class_="inline-edit-value",
                        ),
                        el(
                            "button",
                            "✎",
                            type="button",
                            title=f"Edit {field_name}",
                            class_=(
                                "inline-edit-pencil ml-2 text-primary-500 opacity-0 "
                                "group-hover:opacity-100 transition-opacity text-xs"
                            ),
                            **{"@click": f"{alpine_key} = true"},
                        ),
                        class_="group flex items-center",
                        **{"x-show": f"!{alpine_key}"},
                    ),
                    # Edit mode
                    el(
                        "div",
                        el(
                            "input",
                            type="text",
                            name=field_name,
                            value=str(field_value),
                            class_=(
                                "inline-edit-input border border-border "
                                "rounded px-2 py-1 text-sm w-full "
                                "bg-muted text-foreground "
                                "focus:outline-none focus:ring-2 focus:ring-primary-500"
                            ),
                            **{
                                ":name": f"'{field_name}'",
                                "x-ref": f"input_{field_name}",
                            },
                        ),
                        el(
                            "button",
                            "Save",
                            type="button",
                            class_=(
                                "ml-2 px-2 py-1 text-xs font-medium text-white "
                                "bg-primary-600 hover:bg-primary-700 rounded "
                                "focus:outline-none focus:ring-2 focus:ring-primary-500"
                            ),
                            **{
                                "hx-patch": patch_base,
                                "hx-include": f"[name='{field_name}']",
                                "hx-target": "closest tr",
                                "hx-swap": "outerHTML",
                                "@click": f"{alpine_key} = false",
                            },
                        ),
                        el(
                            "button",
                            "Cancel",
                            type="button",
                            class_=(
                                "ml-1 px-2 py-1 text-xs font-medium text-muted-foreground "
                                "dark:text-muted-foreground hover:text-foreground rounded border "
                                "border-border"
                            ),
                            **{"@click": f"{alpine_key} = false"},
                        ),
                        class_="flex items-center gap-1",
                        **{"x-show": alpine_key},
                    ),
                    class_="py-2 text-sm text-foreground",
                ),
                **{
                    "x-data": f"{{ {alpine_key}: false }}",
                    "class": "border-t border-border",
                },
            )
            field_rows.append(row)

        table_html = render_to_string(
            el("table", *field_rows, class_="detail-inline-edit-table w-full")
        )

        content = f"""
        <div class="resource-header" style="margin-bottom: 1.5rem;">
            <a href="{self._config.prefix}/{self.resource_name}" style="color: #6366f1;">&larr; Back to {label}</a>
            <h1>{label} #{item_id} <span class="text-muted-foreground text-xs">(inline edit)</span></h1>
        </div>
        <div class="resource-content">{table_html}</div>
        """

        is_htmx = wants_fragment(request)
        if is_htmx:
            return HTMLResponse(content)

        return self._renderer.render_page(
            content,
            request=request,
            title=f"{label} #{item_id} — Inline Edit",
            breadcrumbs=[
                {"label": "Dashboard", "url": self._config.prefix},
                {"label": label, "url": f"{self._config.prefix}/{self.resource_name}"},
                {
                    "label": f"#{item_id}",
                    "url": f"{self._config.prefix}/{self.resource_name}/{item_id}",
                },
                {
                    "label": "Inline Edit",
                    "url": f"{self._config.prefix}/{self.resource_name}/{item_id}/inline-edit",
                },
            ],
        )

    async def _get_item_html(self, resource, item_id: str, label: str) -> str:
        """Get HTML representation of the item."""
        if resource and hasattr(resource, "service") and resource.service:
            try:
                if hasattr(resource.service, "get"):
                    item = await resource.service.get(item_id)
                    if item:
                        item_dict = (
                            item.model_dump()
                            if hasattr(item, "model_dump")
                            else dict(item)
                        )
                        rows = [
                            el("tr", el("td", el("strong", k)), el("td", str(v)))
                            for k, v in item_dict.items()
                        ]
                        return render_to_string(
                            el("table", *rows, class_="detail-table")
                        )
                    return render_to_string(el("p", "Item not found"))
            except DataError as e:
                logger.debug(
                    "Failed to get item %s/%s: %s",
                    self.resource_name,
                    item_id,
                    e,
                )
                raise DataError(
                    message=f"Failed to retrieve {self.resource_name} item {item_id}",
                    original_error=e,
                ) from None

        return render_to_string(el("p", f"Item #{item_id}"))


__all__ = ["DetailRenderer"]
