"""Bulk actions for the resource controller."""

from __future__ import annotations

import inspect
from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from lexigram.admin.controllers.resource.meta import ResourceMeta
from lexigram.admin.state.context import AdminContextManager
from lexigram.admin.ui.molecules.toast_notification import ToastNotification
from lexigram.admin.ui.organisms.admin_slide_over import render_bulk_delete_confirm
from lexigram.ui import el, render_to_string


class ResourceBulkMixin:
    """Bulk action confirmations and execution."""

    # Host attributes provided by sibling mixins on ResourceController.
    meta: ResourceMeta

    get_data_source: Any

    async def _record_bulk_permission(self, hook: Any, item: Any) -> bool:
        """Evaluate a sync/async record permission hook fail-closed."""
        try:
            result = hook(item)
            return bool(await result) if inspect.isawaitable(result) else bool(result)
        except Exception:  # noqa: BLE001 — authorization must fail closed
            return False

    async def bulk_delete_confirm(self, request: Request) -> Response:
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

    async def bulk_purge_confirm(self, request: Request) -> Response:
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

    async def bulk_restore_confirm(self, request: Request) -> Response:
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

    async def bulk_action(self, request: Request) -> Response:
        """Handle bulk actions."""
        async with AdminContextManager(request) as ctx:
            form_data = request.scope.get("admin_form_data")
            if form_data is None:
                form_data = await request.form()
            action = form_data.get("action")
            ids = form_data.getlist("ids")

            if not action or not ids:
                return HTMLResponse("Missing action or ids", status_code=400)

            required_capability = {
                "delete": "can_delete",
                "purge": "can_delete",
                "restore": "can_update",
            }.get(str(action))
            capabilities = getattr(getattr(request, "state", None), "permissions", None)
            if (
                required_capability
                and isinstance(capabilities, dict)
                and not capabilities.get(required_capability, False)
            ):
                return HTMLResponse("Forbidden", status_code=403)

            result = await self.execute_bulk_action(str(action), ids)  # type: ignore[arg-type]
            message = str(result)

            ToastNotification.make(message).success().title("Bulk action").send()
            if ctx.is_htmx:
                response = HTMLResponse(render_to_string(el("p", message)))
                response.headers["HX-Trigger"] = (
                    '{"refresh-list":true,"show-toast":{"message":"'
                    + message.replace('"', '\\"')
                    + '","type":"success"}}'
                )
                return response

            return RedirectResponse(
                url=f"{self.meta.prefix}/{self.meta.name}",
                status_code=302,
            )

    async def execute_bulk_action(self, action: str, ids: list[str]) -> str:
        """Execute bulk action. Override to add custom actions.

        When the record count meets or exceeds the configured
        ``bulk_threshold`` (from ``TasksIntegrationConfig``), the action is
        dispatched through the tasks integration instead of running inline.
        """
        data_source = self.get_data_source()
        action = {"delete_selected": "delete"}.get(action, action)

        if action in ("delete", "purge"):
            # Honor the resource's per-record can_delete hook, mirroring
            # the single-record delete path (ResourceMutationMixin /
            # action_handlers._execute_delete).  Without this the bulk
            # route — gated only by identity-level request authz — could
            # bulk-delete records the resource policy forbids.
            can_delete = getattr(self, "can_delete", None)
            if can_delete:
                for item_id in ids:
                    item = await data_source.find_one(item_id)
                    if item is not None and not await self._record_bulk_permission(
                        can_delete, item
                    ):
                        return f"Refused: record {item_id} is protected from deletion"
            if self._should_dispatch_via_tasks(len(ids)):
                return await self._dispatch_via_tasks(action, ids)
            count = await data_source.bulk_delete(ids)
            verb = "Purged" if action == "purge" else "Deleted"
            return f"{verb} {count} items"

        if action == "restore":
            can_update = getattr(self, "can_update", None)
            for item_id in ids:
                item = await data_source.find_one(item_id)
                if item is None:
                    continue
                if can_update and not await self._record_bulk_permission(
                    can_update, item
                ):
                    return f"Refused: record {item_id} is protected from update"
            if self._should_dispatch_via_tasks(len(ids)):
                return await self._dispatch_via_tasks(action, ids)
            restored = 0
            for item_id in ids:
                updated = await data_source.update(item_id, {"deleted_at": None})
                if updated is not None:
                    restored += 1
            return f"Restored {restored} items"

        return f"Unknown action: {action}"

    def _should_dispatch_via_tasks(self, count: int) -> bool:
        """Check if the bulk count exceeds the tasks threshold."""
        from lexigram.admin.integrations import get as get_integration

        tasks = get_integration("TasksIntegration")
        if not tasks:
            return False
        if not tasks._enabled:
            return False
        return count >= tasks.threshold

    async def _dispatch_via_tasks(self, action: str, ids: list[str]) -> str:
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
