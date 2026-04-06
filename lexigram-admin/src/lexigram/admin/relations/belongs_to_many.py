"""BelongsToMany (many-to-many) relation manager with pivot data support."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.relations.manager_ext import RelationManager
from lexigram.serialization import loads_str

if TYPE_CHECKING:
    from collections.abc import Sequence

    from starlette.requests import Request
    from starlette.responses import Response


class BelongsToManyRelationManager(RelationManager):
    """Relation manager for many-to-many relationships through a pivot table.

    Provides attach/detach/sync operations and inline pivot data
    editing for each related record.

    Example:
        class UserRolesRelationManager(BelongsToManyRelationManager):
            relationship_name = "roles"
            pivot_table = "user_roles"
            pivot_columns = ["assigned_at", "is_primary"]
            related_key = "role_id"
            related_key_local = "user_id"

            async def get_query(self):
                return await role_service.list()
    """

    pivot_table: str = ""
    pivot_columns: list[str] = []
    related_key: str = "related_id"
    related_key_local: str = "parent_id"

    @classmethod
    def table(cls, table_config: Any = None) -> list[Any]:
        return []

    async def attach(
        self, related_id: str, pivot_data: dict[str, Any] | None = None
    ) -> None:
        """Attach a related record with optional pivot data."""

    async def detach(self, related_id: str) -> None:
        """Detach a related record."""

    async def sync(
        self,
        related_ids: Sequence[str],
        pivot_data_map: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """Sync related records, detaching any not in the list and attaching new ones.

        Args:
            related_ids: IDs to keep attached.
            pivot_data_map: Optional mapping of related_id -> pivot data.
        """

    async def get_attached_ids(self) -> list[str]:
        """Return IDs of currently attached related records."""
        return []

    async def get_pivot_data(self, related_id: str) -> dict[str, Any] | None:
        """Return pivot data for a single attached record."""
        return None

    async def update_pivot(self, related_id: str, pivot_data: dict[str, Any]) -> None:
        """Update pivot data for an attached record."""

    async def render(self, request: Request, resource_name: str = "") -> str:
        items = await self.get_query()
        attached_ids = await self.get_attached_ids()
        rel_name = self.get_relationship_name()

        rows_html = ""
        for item in items:
            item_id = str(getattr(item, "id", ""))
            is_attached = item_id in attached_ids
            label = str(getattr(item, "name", item_id))

            pivot_data = await self.get_pivot_data(item_id) if is_attached else None
            pivot_cells = self._render_pivot_cells(item_id, pivot_data)

            checked = "checked" if is_attached else ""
            row = f"""<tr class="{"bg-primary-50 dark:bg-primary-900/20" if is_attached else ""}">
                <td class="px-4 py-2">
                    <input type="checkbox" class="belongs-to-many-checkbox rounded border-border text-primary-600 focus:ring-primary-500"
                           data-related-id="{item_id}" {checked}
                           hx-post="/admin/{resource_name}/{self.parent_id}/relations/{rel_name}/toggle"
                           hx-vals='{{"related_id": "{item_id}"}}'
                           hx-target="closest tr" hx-swap="outerHTML" />
                </td>
                <td class="px-4 py-2 text-sm text-foreground">{label}</td>
                {pivot_cells}
                <td class="px-4 py-2 text-sm text-muted-foreground">{item_id}</td>
            </tr>"""
            rows_html += row

        header = f"""<div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-medium text-foreground">{rel_name.replace("_", " ").title()}</h3>
            <div class="flex gap-2">
                <input type="text" class="px-3 py-1.5 text-sm border rounded-lg"
                       placeholder="Search..." id="search-{rel_name}"
                       hx-trigger="keyup changed delay:300ms"
                       hx-get="/admin/{resource_name}/{self.parent_id}/relations/{rel_name}"
                       hx-target="#relation-panel-{rel_name}" hx-select=".relation-panel" />
            </div>
        </div>"""

        table = f"""<table class="min-w-full divide-y divide-border">
            <thead class="bg-muted dark:bg-card">
                <tr>
                    <th class="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase">Attach</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase">Record</th>
                    {self._render_pivot_headers()}
                    <th class="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase">ID</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-border">{rows_html}</tbody>
        </table>"""

        return f"""<div class="relation-panel p-4" id="relation-panel-{rel_name}">
            {header}
            {table}
            <div class="mt-3 flex gap-2">
                <button type="button" class="px-3 py-1.5 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700"
                        hx-post="/admin/{resource_name}/{self.parent_id}/relations/{rel_name}/sync"
                        hx-target="#relation-panel-{rel_name}" hx-swap="outerHTML">Save</button>
            </div>
        </div>"""

    def _render_pivot_headers(self) -> str:
        if not self.pivot_columns:
            return ""
        return "".join(
            f'<th class="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase">{c.replace("_", " ").title()}</th>'
            for c in self.pivot_columns
        )

    def _render_pivot_cells(
        self, related_id: str, pivot_data: dict[str, Any] | None
    ) -> str:
        if not self.pivot_columns:
            return ""
        cells = ""
        for col in self.pivot_columns:
            value = (pivot_data or {}).get(col, "")
            cells += f"""<td class="px-4 py-2">
                <input type="text" class="px-2 py-1 text-sm border rounded w-full"
                       value="{value}" name="pivot_{col}_{related_id}"
                       hx-post="/admin/{self.parent_id}/relations/{self.get_relationship_name()}/pivot/{related_id}"
                       hx-trigger="change" hx-swap="none" />
            </td>"""
        return cells

    def get_pivot_routes(self, resource_name: str) -> list[Any]:
        """Return additional routes for pivot operations."""
        from starlette.responses import HTMLResponse
        from starlette.routing import Route

        prefix = f"/admin/{resource_name}/{self.parent_id}/relations/{self.get_relationship_name()}"

        async def _handle_toggle(request: Any) -> Response:
            if request.headers.get("content-type") == "application/json":
                body = await request.json()
            else:
                body = request.scope.get("admin_form_data")
                if body is None:
                    body = await request.form()
            related_id = body.get("related_id", "")
            attached = await self.get_attached_ids()
            if related_id in attached:
                await self.detach(related_id)
            else:
                await self.attach(related_id)
            return await self._render_single_row(request, resource_name, related_id)

        async def _handle_sync(request: Any) -> Response:
            if request.headers.get("content-type") == "application/json":
                body = await request.json()
            else:
                body = request.scope.get("admin_form_data")
                if body is None:
                    body = await request.form()
            raw_ids = body.get("related_ids", "")
            if isinstance(raw_ids, str):
                ids = (
                    loads_str(raw_ids)
                    if raw_ids.startswith("[")
                    else raw_ids.split(",")
                )
            else:
                ids = raw_ids or []
            await self.sync(ids)
            html = await self.render(request, resource_name)
            return HTMLResponse(html)

        async def _handle_pivot_update(request: Any) -> Response:
            related_id = request.path_params.get("related_id", "")
            form = request.scope.get("admin_form_data")
            if form is None:
                form = await request.form()
            pivot_data = dict(form)
            await self.update_pivot(related_id, pivot_data)
            return HTMLResponse("")

        return [
            Route(f"{prefix}/toggle", _handle_toggle, methods=["POST"]),
            Route(f"{prefix}/sync", _handle_sync, methods=["POST"]),
            Route(
                f"{prefix}/pivot/{{related_id}}", _handle_pivot_update, methods=["POST"]
            ),
        ]

    async def _render_single_row(
        self, request: Any, resource_name: str, related_id: str
    ) -> Any:
        from starlette.responses import HTMLResponse

        items = await self.get_query()
        attached_ids = await self.get_attached_ids()
        item = next((i for i in items if str(getattr(i, "id", "")) == related_id), None)
        if item is None:
            return HTMLResponse("")

        is_attached = related_id in attached_ids
        label = str(getattr(item, "name", related_id))
        pivot_data = await self.get_pivot_data(related_id) if is_attached else None
        pivot_cells = self._render_pivot_cells(related_id, pivot_data)
        checked = "checked" if is_attached else ""

        row = f"""<tr class="{"bg-primary-50 dark:bg-primary-900/20" if is_attached else ""}">
            <td class="px-4 py-2">
                <input type="checkbox" class="belongs-to-many-checkbox rounded border-border text-primary-600 focus:ring-primary-500"
                       data-related-id="{related_id}" {checked}
                       hx-post="/admin/{resource_name}/{self.parent_id}/relations/{self.get_relationship_name()}/toggle"
                       hx-vals='{{"related_id": "{related_id}"}}'
                       hx-target="closest tr" hx-swap="outerHTML" />
            </td>
            <td class="px-4 py-2 text-sm text-foreground">{label}</td>
            {pivot_cells}
            <td class="px-4 py-2 text-sm text-muted-foreground">{related_id}</td>
        </tr>"""
        return HTMLResponse(row)
