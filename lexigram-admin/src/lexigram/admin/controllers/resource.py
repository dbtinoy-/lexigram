"""Resource controller for CRUD operations.

Provides a base controller class for handling resource CRUD with
HTMX support, automatic pagination, filtering, and bulk actions.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from lexigram.admin.data.data_source import IDataSource as DataSourceProtocol
from lexigram.admin.data.data_source import QueryResult
from lexigram.admin.data.query import QuerySpec
from lexigram.admin.exceptions import AdminValidationError, NotFoundError
from lexigram.admin.state.context import AdminContext, AdminContextManager
from lexigram.admin.state.url import URLState
from lexigram.admin.ui.organisms.admin_slide_over import (
    render_bulk_delete_confirm,
    render_delete_confirm,
)
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.ui import el, render_to_string

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class ResourceMeta:
    """Metadata for a resource."""

    name: str
    label: str
    label_plural: str
    icon: str | None = None

    # URLs
    prefix: str = ""

    # Default settings
    per_page: int = 20
    searchable_fields: list[str] | None = None
    default_sort: str = "id"
    default_sort_order: str = "desc"

    # Features
    enable_create: bool = True
    enable_edit: bool = True
    enable_delete: bool = True
    enable_clone: bool = True
    enable_bulk_actions: bool = True
    enable_export: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResourceMeta:
        """Create from dictionary."""
        return cls(
            name=data.get("name", ""),
            label=data.get("label", ""),
            label_plural=data.get("label_plural", ""),
            icon=data.get("icon"),
            prefix=data.get("prefix", ""),
            per_page=data.get("per_page", 20),
            searchable_fields=data.get("searchable_fields"),
            default_sort=data.get("default_sort", "id"),
            default_sort_order=data.get("default_sort_order", "desc"),
            enable_create=data.get("enable_create", True),
            enable_edit=data.get("enable_edit", True),
            enable_delete=data.get("enable_delete", True),
            enable_clone=data.get("enable_clone", True),
            enable_bulk_actions=data.get("enable_bulk_actions", True),
            enable_export=data.get("enable_export", True),
        )


@inject
class ResourceController(ABC, Generic[T]):
    """Base controller for resource CRUD operations.

    Provides standard CRUD endpoints with HTMX support:
    - GET  /{resource}           - List with pagination/filtering
    - GET  /{resource}/{id}      - View single resource
    - GET  /{resource}/create    - Create form
    - POST /{resource}           - Create resource
    - GET  /{resource}/{id}/edit - Edit form
    - PUT  /{resource}/{id}      - Update resource
    - DELETE /{resource}/{id}    - Delete resource
    - POST /{resource}/bulk      - Bulk actions

    Subclasses should implement:
    - get_data_source() - Return DataSourceProtocol for this resource
    - get_columns() - Return columns for list view
    - render_list() - Render list view HTML
    - render_detail() - Render detail view HTML
    - render_form() - Render create/edit form HTML
    """

    meta: ResourceMeta

    # When True, DELETE calls soft-delete (sets deleted_at) instead of hard-delete.
    # Use RepositoryDataSource(soft_delete_enabled=True) to filter them in queries.
    soft_delete_enabled: bool = False

    def __init__(
        self,
        data_source: DataSourceProtocol[T] | None = None,
        meta: ResourceMeta | None = None,
    ):
        self._data_source = data_source
        if meta:
            self.meta = meta
        # Optional audit logger — set via set_audit_logger() or DI
        self._audit_logger: Any = None
        # Optional revision service — set via set_revision_service() or DI
        self._revision_service: Any = None

    def set_audit_logger(self, audit_logger: Any) -> None:
        """Attach an audit logger for CRUD event tracking.

        Args:
            audit_logger: Any object implementing ``async log(AuditEntry) -> None``.
        """
        self._audit_logger = audit_logger

    def set_revision_service(self, revision_service: Any) -> None:
        """Attach a :class:`~lexigram.admin.services.revisions.RevisionService`.

        When set, a snapshot is recorded after every successful create or
        update. The service also exposes ``diff`` and ``revert_data`` for the
        revision history UI.

        Args:
            revision_service: ``RevisionService`` instance.
        """
        self._revision_service = revision_service

    async def _record_revision(
        self,
        request: Request,
        resource_id: str,
        data: dict[str, Any],
        comment: str = "",
    ) -> None:
        """Silently create a revision snapshot if a service is attached.

        Args:
            request: Current HTTP request (actor identity extracted from state).
            resource_id: Record identifier.
            data: Full field snapshot to persist.
            comment: Optional human-readable description.
        """
        if self._revision_service is None:
            return
        try:
            user = getattr(request.state, "user", None)
            actor_id = str(getattr(user, "id", getattr(user, "user_id", "system")))
            resource_name = getattr(self.meta, "name", "resource")
            await self._revision_service.record(
                resource_name,
                resource_id,
                data,
                actor_id=actor_id,
                comment=comment,
            )
        except Exception:  # noqa: BLE001
            logger.warning(
                "Revision recording failed for resource %s/%s",
                getattr(self.meta, "name", ""),
                resource_id,
            )

    async def _emit_audit(
        self,
        request: Request,
        action: str,
        item_id: str = "",
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        outcome: str = "success",
    ) -> None:
        """Emit an audit log entry if a logger is attached.

        Args:
            request: Current HTTP request (used for actor identity and metadata).
            action: Machine-readable action (e.g. ``"user.create"``).
            item_id: Identifier of the affected record.
            old_values: Field snapshot before the change.
            new_values: Field snapshot after the change.
            outcome: ``"success"`` or ``"failure"``.
        """
        if self._audit_logger is None:
            return
        try:
            from lexigram.contracts.audit import AuditEntry

            user = getattr(request.state, "user", None)
            actor_id = str(getattr(user, "id", getattr(user, "user_id", "anonymous")))
            resource_name = getattr(self.meta, "name", "unknown")
            entry = AuditEntry(
                action=action,
                actor_id=actor_id,
                resource_type=resource_name,
                resource_id=str(item_id),
                outcome=outcome,
                old_values=old_values,
                new_values=new_values,
                metadata={
                    "ip": request.client.host if request.client else "",
                    "user_agent": request.headers.get("user-agent", ""),
                    "path": str(request.url),
                },
            )
            await self._audit_logger.log(entry)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Audit logging failed for action %s on %s/%s",
                action,
                getattr(self.meta, "name", ""),
                item_id,
            )

    def get_data_source(self) -> DataSourceProtocol[T]:
        """Get the data source for this resource."""
        if self._data_source is None:
            raise NotImplementedError("Subclass must implement get_data_source()")
        return self._data_source

    # ========== List ==========

    async def list_view(self, request: Request) -> Response:
        """List resources with pagination and filtering."""
        async with AdminContextManager(request) as ctx:
            # Parse URL state
            url_state = URLState.from_request(request)

            # Build query
            query = self._build_query(url_state)

            # Fetch data
            data_source = self.get_data_source()
            result = await data_source.find_many(query)

            # Check if HTMX request
            if ctx.is_htmx:
                # Return just the table/content
                return HTMLResponse(self.render_list_partial(ctx, result, url_state))

            # Return full page
            return HTMLResponse(self.render_list(ctx, result, url_state))

    def _build_query(self, state: URLState) -> QuerySpec:
        """Build QuerySpec from URL state."""
        qs = QuerySpec()

        # Pagination — cursor takes priority over page number
        if state.cursor:
            qs = qs.with_cursor(state.cursor).with_per_page(
                state.per_page or self.meta.per_page
            )
        else:
            qs = qs.with_page(state.page).with_per_page(
                state.per_page or self.meta.per_page
            )

        # Sorting
        if state.sort:
            qs = qs.with_order_by(state.sort, state.order)
        else:
            qs = qs.with_order_by(self.meta.default_sort, self.meta.default_sort_order)

        # Search
        if state.search:
            qs = qs.with_search(state.search, self.meta.searchable_fields or [])

        # Filters
        for field, value in state.filters.items():
            if isinstance(value, list):
                qs = qs.with_where_in(field, value)
            else:
                qs = qs.with_where_eq(field, value)

        return qs

    # ========== Detail ==========

    async def detail(self, request: Request) -> Response:
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

    # ========== Create ==========

    async def create_form(self, request: Request) -> Response:
        """Show create form."""
        async with AdminContextManager(request) as ctx:
            if ctx.is_htmx:
                return HTMLResponse(self.render_form_partial(ctx, None))
            return HTMLResponse(self.render_form(ctx, None))

    async def create(self, request: Request) -> Response:
        """Create new resource."""
        async with AdminContextManager(request) as ctx:
            form_data = request.scope.get("admin_form_data")
            if form_data is None:
                form_data = await request.form()
            data = dict(form_data)

            # Validate
            try:
                validated = self.validate_create(data)
            except AdminValidationError as e:
                # Return form with errors
                if ctx.is_htmx:
                    return HTMLResponse(
                        self.render_form_partial(ctx, None, data, e.details or {}),
                        status_code=422,
                    )
                return HTMLResponse(
                    self.render_form(ctx, None, data, e.details or {}),
                    status_code=422,
                )

            # Create
            data_source = self.get_data_source()
            created = await data_source.create(validated)
            created_id = str(getattr(created, "id", "") if created else "")
            await self._emit_audit(
                request,
                f"{getattr(self.meta, 'name', 'resource')}.create",
                item_id=created_id,
                new_values=validated,
            )
            await self._record_revision(
                request, created_id, validated, comment="create"
            )

            # Redirect or return success
            ctx.add_flash("Created successfully", "success")
            if ctx.is_htmx:
                response = Response(status_code=200)
                response.headers["HX-Redirect"] = f"{self.meta.prefix}/{self.meta.name}"
                return response

            return RedirectResponse(
                url=f"{self.meta.prefix}/{self.meta.name}",
                status_code=302,
            )

    def validate_create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate data for create. Override to customize."""
        return data

    # ========== Update ==========

    async def edit_form(self, request: Request) -> Response:
        """Show edit form."""
        async with AdminContextManager(request) as ctx:
            item_id = request.path_params.get("id")

            data_source = self.get_data_source()
            item = await data_source.find_one(item_id)

            if item is None:
                raise NotFoundError(message=f"{self.meta.label} not found")

            if ctx.is_htmx:
                return HTMLResponse(self.render_form_partial(ctx, item))
            return HTMLResponse(self.render_form(ctx, item))

    async def update(self, request: Request) -> Response:
        """Update existing resource."""
        async with AdminContextManager(request) as ctx:
            item_id = request.path_params.get("id")
            form_data = request.scope.get("admin_form_data")
            if form_data is None:
                form_data = await request.form()
            data = dict(form_data)

            # Validate
            try:
                validated = self.validate_update(item_id, data)
            except AdminValidationError as e:
                # Get current item for form
                item = await self.get_data_source().find_one(item_id)
                if ctx.is_htmx:
                    return HTMLResponse(
                        self.render_form_partial(ctx, item, data, e.details or {}),
                        status_code=422,
                    )
                return HTMLResponse(
                    self.render_form(ctx, item, data, e.details or {}),
                    status_code=422,
                )

            # Update
            data_source = self.get_data_source()
            item = await data_source.find_one(item_id)
            can_update = getattr(self, "can_update", None)
            if can_update and not can_update(item):
                return HTMLResponse("This record cannot be updated", status_code=403)
            item = await data_source.update(item_id, validated)
            await self._emit_audit(
                request,
                f"{getattr(self.meta, 'name', 'resource')}.update",
                item_id=str(item_id),
                new_values=validated,
            )
            await self._record_revision(
                request, str(item_id), validated, comment="update"
            )

            ctx.add_flash("Updated successfully", "success")
            if ctx.is_htmx:
                response = Response(status_code=200)
                response.headers["HX-Redirect"] = (
                    f"{self.meta.prefix}/{self.meta.name}/{item_id}"
                )
                return response

            return RedirectResponse(
                url=f"{self.meta.prefix}/{self.meta.name}/{item_id}",
                status_code=302,
            )

    def validate_update(self, item_id: Any, data: dict[str, Any]) -> dict[str, Any]:
        """Validate data for update. Override to customize."""
        return data

    # ========== Delete ==========

    async def delete_confirm(self, request: Request) -> Response:
        """Render a delete confirmation slide-over panel.

        Called via HTMX GET from the Delete row action. Returns an
        AdminSlideOver fragment that lets the user confirm or cancel
        the deletion without using the native browser confirm dialog.
        """
        item_id = request.path_params.get("id")
        label = self.meta.label

        # Attempt to fetch a human-readable label for the record
        record_label = f"{label} #{item_id}"
        try:
            data_source = self.get_data_source()
            item = await data_source.find_one(item_id)
            if item:
                for field in ("name", "title", "email", "username", "label"):
                    val = getattr(item, field, None)
                    if val:
                        record_label = str(val)
                        break
        except Exception:  # noqa: BLE001
            pass

        delete_url = f"{self.meta.prefix}/{self.meta.name}/{item_id}"
        html = render_delete_confirm(
            record_label=record_label,
            delete_url=delete_url,
        )
        return HTMLResponse(html)

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

    # ── Import downloads (example CSV / failed-import report) ──
    # The base controller has no resource reference; subclasses can set
    # `self._import_action = ImportAction(...)` in their __init__ to
    # enable the download routes.

    def _find_import_action(self) -> Any:
        """Return the configured ImportAction, or None."""
        return getattr(self, "_import_action", None)

    async def import_example(self, request: Request) -> Response:
        """Serve the resource's import example CSV template as a download."""
        action = self._find_import_action()
        if action is None or not action.example_csv():
            return HTMLResponse(
                "<h1>Import not configured for this resource</h1>",
                status_code=404,
            )
        return Response(
            content=action.example_csv(),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{action.example_filename}"'
                )
            },
        )

    async def import_report(self, request: Request) -> Response:
        """Serve a stored failed-import report as a CSV download."""
        action = self._find_import_action()
        report_id = request.query_params.get("report_id", "")
        content = action.report_csv(report_id) if action else None
        if content is None:
            return HTMLResponse("<h1>Report not found</h1>", status_code=404)
        filename = action.report_filename(report_id) or "import-errors.csv"
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    async def delete(self, request: Request) -> Response:
        """Delete resource (soft or hard depending on soft_delete_enabled)."""
        async with AdminContextManager(request) as ctx:
            item_id = request.path_params.get("id")
            data_source = self.get_data_source()

            if self.soft_delete_enabled:
                # Soft delete — stamp deleted_at instead of removing the row
                updated = await data_source.update(
                    item_id, {"deleted_at": datetime.now(UTC).isoformat()}
                )
                if updated is None:
                    raise NotFoundError(message=f"{self.meta.label} not found")
                await self._emit_audit(
                    request,
                    f"{getattr(self.meta, 'name', 'resource')}.soft_delete",
                    item_id=str(item_id),
                )
            else:
                success = await data_source.delete(item_id)
                if not success:
                    raise NotFoundError(message=f"{self.meta.label} not found")
                await self._emit_audit(
                    request,
                    f"{getattr(self.meta, 'name', 'resource')}.delete",
                    item_id=str(item_id),
                )

            ctx.add_flash("Deleted successfully", "success")
            if ctx.is_htmx:
                response = Response(status_code=200)
                response.headers["HX-Redirect"] = f"{self.meta.prefix}/{self.meta.name}"
                return response

            return RedirectResponse(
                url=f"{self.meta.prefix}/{self.meta.name}",
                status_code=302,
            )

    async def restore(self, request: Request) -> Response:
        """Restore a soft-deleted resource (clears deleted_at).

        Only available when soft_delete_enabled is True.
        """
        async with AdminContextManager(request) as ctx:
            if not self.soft_delete_enabled:
                return HTMLResponse(
                    "Soft delete is not enabled for this resource", status_code=400
                )

            item_id = request.path_params.get("id")
            data_source = self.get_data_source()

            updated = await data_source.update(item_id, {"deleted_at": None})
            if updated is None:
                raise NotFoundError(message=f"{self.meta.label} not found")
            await self._emit_audit(
                request,
                f"{getattr(self.meta, 'name', 'resource')}.restore",
                item_id=str(item_id),
            )

            ctx.add_flash("Restored successfully", "success")
            if ctx.is_htmx:
                response = Response(status_code=200)
                response.headers["HX-Trigger"] = (
                    '{"refresh-list":true,"show-toast":{"message":"Restored successfully","type":"success"}}'
                )
                return response

            return RedirectResponse(
                url=f"{self.meta.prefix}/{self.meta.name}",
                status_code=302,
            )

    # ========== Bulk Actions ==========

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

    async def execute_bulk_action(self, action: str, ids: list[str]) -> str:
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

    # ========== Rendering (Override these) ==========

    def render_list(
        self,
        ctx: AdminContext,
        result: QueryResult[T],
        state: URLState,
    ) -> str:
        """Render full list page. Override in subclass."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{self.meta.label_plural}</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
</head>
<body>
    <h1>{self.meta.label_plural}</h1>
    {self.render_list_partial(ctx, result, state)}
</body>
</html>
"""

    def render_list_partial(
        self,
        ctx: AdminContext,
        result: QueryResult[T],
        state: URLState,
    ) -> str:
        """Render list content (for HTMX). Override in subclass."""
        row_els: list[Any] = []
        for item in result.items:
            row_els.append(el("tr", el("td", str(item))))

        total_pages = getattr(result, "total_pages", "?")
        return f"""
<table>
    <thead><tr><th>Item</th></tr></thead>
    {render_to_string(el("tbody", *row_els))}
</table>
<div>Page {result.page} of {total_pages}</div>
"""

    def render_detail(self, ctx: AdminContext, item: T) -> str:
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

    def render_detail_partial(self, ctx: AdminContext, item: T) -> str:
        """Render detail content. Override in subclass."""
        return render_to_string(el("pre", str(item)))

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

    # ========== Route Registration ==========

    def get_routes(self) -> list:
        """Get Starlette routes for this controller."""
        from starlette.routing import Route

        prefix = f"/{self.meta.name}"

        return [
            Route(prefix, self.list_view, methods=["GET"]),
            Route(f"{prefix}/create", self.create_form, methods=["GET"]),
            Route(prefix, self.create, methods=["POST"]),
            Route(f"{prefix}/bulk", self.bulk_action, methods=["POST"]),
            Route(
                f"{prefix}/bulk-delete-confirm",
                self.bulk_delete_confirm,
                methods=["GET"],
            ),
            Route(
                f"{prefix}/bulk-purge-confirm",
                self.bulk_purge_confirm,
                methods=["GET"],
            ),
            Route(
                f"{prefix}/bulk-restore-confirm",
                self.bulk_restore_confirm,
                methods=["GET"],
            ),
            Route(f"{prefix}/import-example", self.import_example, methods=["GET"]),
            Route(f"{prefix}/import-report", self.import_report, methods=["GET"]),
            Route(f"{prefix}/{{id}}", self.detail, methods=["GET"]),
            Route(f"{prefix}/{{id}}/edit", self.edit_form, methods=["GET"]),
            Route(
                f"{prefix}/{{id}}/delete-confirm", self.delete_confirm, methods=["GET"]
            ),
            Route(f"{prefix}/{{id}}", self.update, methods=["PUT", "POST"]),
            Route(f"{prefix}/{{id}}", self.delete, methods=["DELETE"]),
        ]
