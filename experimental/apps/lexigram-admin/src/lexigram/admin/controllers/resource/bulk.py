"""Bulk actions for the resource controller."""

from __future__ import annotations

import inspect
from typing import Any, cast

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from lexigram.admin.controllers.resource.meta import ResourceMeta
from lexigram.admin.state.context import AdminContextManager
from lexigram.admin.ui.molecules.toast_notification import ToastNotification
from lexigram.admin.ui.organisms.admin_slide_over import render_bulk_delete_confirm
from lexigram.ui import el, render_to_string

#: Bulk action names that produce a direct file download instead of a
#: toast, mapped to their default file format (B29).
_EXPORT_BULK_ACTIONS: dict[str, str] = {
    "export": "csv",
    "export_csv": "csv",
    "export_json": "json",
    "export_xlsx": "xlsx",
}

#: Direct-download formats the bulk export branch can encode (R29 adds xlsx).
_EXPORT_FORMATS = ("csv", "json", "xlsx")

#: Hard caps for id-less "export the filtered view" requests (R25).
MAX_FILTERED_EXPORT_ROWS = 10_000
_FILTERED_EXPORT_PAGE_SIZE = 1000
_MAX_LIST_QUERY_LENGTH = 4096


class ResourceBulkMixin:
    """Bulk action confirmations and execution."""

    # Host attributes provided by sibling mixins on ResourceController.
    meta: ResourceMeta

    get_data_source: Any

    _build_query: Any  # ResourceListMixin — reused for filtered exports.

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
            # Starlette's multipart form typing includes UploadFile, but this
            # field is intentionally an ID-only control. Reject non-string
            # values rather than coercing an uploaded file into an ID.
            ids = [value for value in form_data.getlist("ids") if isinstance(value, str)]

            # R25: an export submitted with scope=filtered and no ids means
            # "export everything matching the current list view".
            scope = str(form_data.get("scope") or "").strip().lower()
            filtered_export = (
                str(action) in _EXPORT_BULK_ACTIONS and scope == "filtered" and not ids
            )

            if not action or (not ids and not filtered_export):
                return HTMLResponse("Missing action or ids", status_code=400)

            required_capability = {
                "delete": "can_delete",
                "purge": "can_delete",
                "restore": "can_update",
                # Exports read data — gate on view capability (B29).
                **dict.fromkeys(_EXPORT_BULK_ACTIONS, "can_view"),
            }.get(str(action))
            capabilities = getattr(getattr(request, "state", None), "permissions", None)
            if (
                required_capability
                and isinstance(capabilities, dict)
                and not capabilities.get(required_capability, False)
            ):
                return HTMLResponse("Forbidden", status_code=403)

            if str(action) in _EXPORT_BULK_ACTIONS:
                # B29: export used to fall through to "Unknown action:
                # export" wrapped in a *success* toast. It now returns a
                # real file download of the selected rows.
                file_format = str(
                    form_data.get("format") or _EXPORT_BULK_ACTIONS[str(action)]
                )
                if filtered_export:
                    return await self.bulk_export_filtered(
                        str(form_data.get("list_query") or ""), file_format
                    )
                return await self.bulk_export(ids, file_format)

            result = await self.execute_bulk_action(str(action), ids)
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

    async def bulk_export(self, ids: list[str], file_format: str = "csv") -> Response:
        """Stream the selected records as a downloadable CSV/JSON file.

        B29: the toolbar export buttons post ``action=export`` to the bulk
        route, which previously had no export branch at all.

        Args:
            ids: Selected record ids, in selection order.
            file_format: ``csv`` (default), ``json``, or ``xlsx``.

        Returns:
            An attachment response, or an error response when the format
            is unsupported / export is disabled for the resource.
        """
        if not getattr(self.meta, "enable_export", True):
            return HTMLResponse("Export is disabled for this resource", status_code=403)

        fmt = (file_format or "csv").strip().lower()
        if fmt not in _EXPORT_FORMATS:
            return HTMLResponse(f"Unsupported export format: {fmt}", status_code=400)

        rows = [self._export_row(item) for item in await self._fetch_export_rows(ids)]
        rows = self._order_rows_by_selection(rows, ids)
        return self._export_attachment(rows, fmt)

    async def bulk_export_filtered(
        self, list_query: str, file_format: str = "csv"
    ) -> Response:
        """Export every record matching the forwarded list state (R25).

        ``list_query`` is the list page's current querystring; it is parsed
        with the same ``URLState`` parser the list view uses, so the export
        matches exactly what the user is looking at. Results are paged and
        hard-capped at ``MAX_FILTERED_EXPORT_ROWS``.

        Args:
            list_query: Raw querystring (no leading ``?``).
            file_format: ``csv`` (default), ``json``, or ``xlsx``.

        Returns:
            An attachment response, or an error response.
        """
        from types import SimpleNamespace

        from starlette.datastructures import QueryParams

        from lexigram.admin.state.url import URLState

        if not getattr(self.meta, "enable_export", True):
            return HTMLResponse("Export is disabled for this resource", status_code=403)

        fmt = (file_format or "csv").strip().lower()
        if fmt not in _EXPORT_FORMATS:
            return HTMLResponse(f"Unsupported export format: {fmt}", status_code=400)

        raw_query = str(list_query or "")
        if len(raw_query) > _MAX_LIST_QUERY_LENGTH:
            return HTMLResponse("List query too long", status_code=400)

        try:
            params = QueryParams(raw_query.lstrip("?"))
            state = URLState.from_request(
                cast("Request", SimpleNamespace(query_params=params))
            )
        except (ValueError, TypeError):
            return HTMLResponse("Invalid list query", status_code=400)
        # Cursor pagination belongs to the interactive list; exports page
        # deterministically from the start of the result set.
        if state.cursor:
            from dataclasses import replace

            state = replace(state, cursor=None)

        data_source = self.get_data_source()
        rows: list[dict[str, Any]] = []
        page = 1
        while len(rows) < MAX_FILTERED_EXPORT_ROWS:
            query = (
                self._build_query(state)
                .with_page(page)
                .with_per_page(_FILTERED_EXPORT_PAGE_SIZE)
            )
            result = await data_source.find_many(query)
            batch = list(result.items)
            if not batch:
                break
            remaining = MAX_FILTERED_EXPORT_ROWS - len(rows)
            rows.extend(self._export_row(item) for item in batch[:remaining])
            if len(batch) < _FILTERED_EXPORT_PAGE_SIZE:
                break
            page += 1
        return self._export_attachment(rows, fmt)

    def _export_attachment(self, rows: list[dict[str, Any]], fmt: str) -> Response:
        """Encode rows as a CSV/JSON/XLSX attachment response."""
        from datetime import UTC, datetime
        import re

        if fmt == "csv":
            payload = self._encode_export_csv(rows)
            media_type = "text/csv; charset=utf-8"
        elif fmt == "xlsx":
            from lexigram.admin.services.export.xlsx import (
                XLSX_CONTENT_TYPE,
                encode_rows_as_xlsx,
            )

            try:
                payload = encode_rows_as_xlsx(rows)
            except ImportError as exc:
                # Optional dependency absent — a clear 501 beats a 500.
                return HTMLResponse(str(exc), status_code=501)
            media_type = XLSX_CONTENT_TYPE
        else:
            from lexigram.serialization import dumps_str

            payload = dumps_str(rows).encode("utf-8")
            media_type = "application/json"

        stem = re.sub(r"[^A-Za-z0-9._-]", "_", str(self.meta.name)) or "export"
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"{stem}_export_{timestamp}.{fmt}"
        return Response(
            content=payload,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                # Exports may contain sensitive data — never cache.
                "Cache-Control": "no-store",
            },
        )

    async def _fetch_export_rows(self, ids: list[str]) -> list[Any]:
        """Fetch the selected records, preferring one batched query."""
        data_source = self.get_data_source()
        try:
            from lexigram.admin.data.query import QuerySpec

            qs = (
                QuerySpec()
                .with_where_in("id", list(ids))
                .with_page(1)
                .with_per_page(max(len(ids), 1))
            )
            result = await data_source.find_many(qs)
            items = list(result.items)
            if items:
                return items
        except Exception:  # noqa: BLE001 — duck-typed data sources may not speak QuerySpec
            pass
        # Fallback: per-id lookups (mirrors the other bulk branches).
        items = []
        for item_id in ids:
            item = await data_source.find_one(item_id)
            if item is not None:
                items.append(item)
        return items

    @staticmethod
    def _export_row(item: Any) -> dict[str, Any]:
        """Normalize a record (mapping or object) to a plain dict."""
        if isinstance(item, dict):
            return dict(item)
        try:
            return dict(item)
        except (TypeError, ValueError):
            attrs = getattr(item, "__dict__", None)
            if isinstance(attrs, dict):
                return {k: v for k, v in attrs.items() if not k.startswith("_")}
            return {"value": str(item)}

    @staticmethod
    def _order_rows_by_selection(
        rows: list[dict[str, Any]], ids: list[str]
    ) -> list[dict[str, Any]]:
        """Return rows in the user's selection order when ids allow it."""
        by_id: dict[str, dict[str, Any]] = {}
        for row in rows:
            rid = row.get("id")
            if rid is None or str(rid) in by_id:
                return rows  # ambiguous — keep data-source order
            by_id[str(rid)] = row
        if len(by_id) != len(rows):
            return rows
        ordered = [by_id[str(i)] for i in ids if str(i) in by_id]
        ordered.extend(row for row in rows if row not in ordered)
        return ordered

    @staticmethod
    def _encode_export_csv(rows: list[dict[str, Any]]) -> bytes:
        """Encode rows as sanitized CSV bytes.

        Cells pass through :func:`sanitize_cell_value` — the same
        formula-injection guard used by the export file backends.
        """
        import csv
        import io

        from lexigram.admin.services.export.sanitize import sanitize_cell_value

        fieldnames: list[str] = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)

        buffer = io.StringIO()
        if fieldnames:
            writer = csv.DictWriter(
                buffer, fieldnames=fieldnames, extrasaction="ignore", restval=""
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {k: sanitize_cell_value(row.get(k)) for k in fieldnames}
                )
        return buffer.getvalue().encode("utf-8")

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
