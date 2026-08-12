"""Bulk actions for the resource controller."""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from lexigram.admin.state.context import AdminContextManager
from lexigram.admin.ui.organisms.admin_slide_over import render_bulk_delete_confirm
from lexigram.ui import el, render_to_string

if TYPE_CHECKING:
    from lexigram.admin.controllers.resource import ResourceController



class ResourceBulkMixin:
    """Bulk action confirmations and execution."""

    async def bulk_delete_confirm(self: ResourceController, request: Request) -> Response:
        """Render a bulk delete confirmation slide-over panel.

        Called via HTMX GET from a BulkAction button. Reads the selected
        record IDs from the query string (passed via ``hx-include`` of the
        checked checkboxes) and renders a slide-over confirmation panel.
        """
        ids = request.query_params.getlist("ids")
        record_count = len(ids)

        bulk_url = f"{self.meta.prefix}/{self.meta.name}/bulk"
        html = render_bulk_delete_confirm(
            record_count=record_count,
            bulk_url=bulk_url,
        )
        return HTMLResponse(html)

    async def bulk_purge_confirm(self: ResourceController, request: Request) -> Response:
        """Render a bulk purge confirmation slide-over panel.

        Called via HTMX GET from a PurgeBulkAction button. Reads the
        selected record IDs from the query string and renders a
        slide-over confirmation panel posting ``action=purge``.
        """
        ids = request.query_params.getlist("ids")
        record_count = len(ids)

        bulk_url = f"{self.meta.prefix}/{self.meta.name}/bulk"
        html = render_bulk_delete_confirm(
            record_count=record_count,
            bulk_url=bulk_url,
            action="purge",
            title="Purge Records",
            heading="Confirm Bulk Purge",
            confirm_phrase="PURGE",
            subtitle=f"Purging {record_count} record{'s' if record_count != 1 else ''}",
            confirm_label="Purge",
            message=(
                f"You are about to permanently purge <strong>{record_count}</strong> "
                f"record{'s' if record_count != 1 else ''}. "
                "This action <strong>cannot be undone</strong>."
            ),
        )
        return HTMLResponse(html)

    async def bulk_restore_confirm(self: ResourceController, request: Request) -> Response:
        """Render a bulk restore confirmation slide-over panel.

        Called via HTMX GET from a RestoreBulkAction button. Reads the
        selected record IDs from the query string and renders a
        slide-over confirmation panel posting ``action=restore``.
        """
        ids = request.query_params.getlist("ids")
        record_count = len(ids)

        bulk_url = f"{self.meta.prefix}/{self.meta.name}/bulk"
        html = render_bulk_delete_confirm(
            record_count=record_count,
            bulk_url=bulk_url,
            action="restore",
            title="Restore Records",
            heading="Confirm Bulk Restore",
            confirm_phrase="RESTORE",
            subtitle=f"Restoring {record_count} record{'s' if record_count != 1 else ''}",
            confirm_label="Restore",
            message=(
                f"You are about to restore <strong>{record_count}</strong> "
                f"soft-deleted record{'s' if record_count != 1 else ''}."
            ),
            variant="default",
            confirm_button_class=(
                "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium "
                "text-white bg-success hover:bg-success/90 "
                "focus:outline-none focus:ring-2 focus:ring-success focus:ring-offset-2 "
                "transition-colors shadow-sm "
                "disabled:opacity-50 disabled:cursor-not-allowed"
            ),
        )
        return HTMLResponse(html)
    async def bulk_action(self: ResourceController, request: Request) -> Response:
        """Handle bulk actions."""
        async with AdminContextManager(request) as ctx:
            form_data = request.scope.get("admin_form_data")
            if form_data is None:
                form_data = await request.form()
            action = form_data.get("action")
            ids = form_data.getlist("ids")

            if not action or not ids:
                return HTMLResponse("Missing action or ids", status_code=400)

            result = await self.execute_bulk_action(action, ids)  # type: ignore[arg-type]

            ctx.add_flash(result, "success")
            if ctx.is_htmx:
                response = HTMLResponse(render_to_string(el("p", str(result))))
                response.headers["HX-Trigger"] = (
                    '{"refresh-list":true,"show-toast":{"message":"'
                    + result.replace('"', '\\"')
                    + '","type":"success"}}'
                )
                return response

            return RedirectResponse(
                url=f"{self.meta.prefix}/{self.meta.name}",
                status_code=302,
            )

    async def execute_bulk_action(self: ResourceController, action: str, ids: list[str]) -> str:
        """Execute bulk action. Override to add custom actions.

        When the record count meets or exceeds the configured
        ``bulk_threshold`` (from ``TasksIntegrationConfig``), the action is
        dispatched through the tasks integration instead of running inline.
        """
        if self._should_dispatch_via_tasks(len(ids)):
            return await self._dispatch_via_tasks(action, ids)

        data_source = self.get_data_source()

        if action == "delete":
            count = await data_source.bulk_delete(ids)
            return f"Deleted {count} items"

        if action == "purge":
            count = await data_source.bulk_delete(ids)
            return f"Purged {count} items"

        if action == "restore":
            restored = 0
            for item_id in ids:
                updated = await data_source.update(item_id, {"deleted_at": None})
                if updated is not None:
                    restored += 1
            return f"Restored {restored} items"

        return f"Unknown action: {action}"

    def _should_dispatch_via_tasks(self: ResourceController, count: int) -> bool:
        """Check if the bulk count exceeds the tasks threshold."""
        from lexigram.admin.integrations import get as get_integration

        tasks = get_integration("TasksIntegration")
        if not tasks:
            return False
        if not tasks._enabled:
            return False
        return count >= tasks.threshold

    async def _dispatch_via_tasks(self: ResourceController, action: str, ids: list[str]) -> str:
        """Dispatch a bulk action through the tasks integration."""
        from lexigram.admin.integrations import get as get_integration

        tasks = get_integration("TasksIntegration")
        if not tasks:
            return "Task system unavailable"

        result = await tasks.dispatch(
            runner=action,
            action_name=action,
            record_ids=ids,
            ctx_summary=f"Bulk {action} of {len(ids)} records",
        )
        return f"Scheduled bulk {action} for {len(ids)} records (task: {result.get('status', 'unknown')})"
