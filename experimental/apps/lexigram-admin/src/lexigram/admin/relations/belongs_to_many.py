"""BelongsToMany (many-to-many) relation manager with pivot data support."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.data.query import QuerySpec
from lexigram.admin.relations.errors import RelationPersistenceError
from lexigram.admin.relations.manager_ext import RelationManager
from lexigram.serialization import dumps_str, loads_str
from lexigram.ui import el, render_to_string

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

    def _require_persistence(self) -> None:
        """Raise unless pivot persistence is configured."""
        if not self.pivot_table:
            raise RelationPersistenceError(
                "BelongsToManyRelationManager requires a pivot_table "
                f"({self.get_relationship_name()})"
            )
        if self._data_source is None:
            raise RelationPersistenceError(
                "BelongsToManyRelationManager requires an attached data source; "
                "pass data_source to the constructor or call set_data_source()"
            )

    def _row_id(self, row: Any) -> Any:
        """Extract a row's primary key."""
        if isinstance(row, dict):
            return row.get("id") or row.get("pk")
        return getattr(row, "id", None) or getattr(row, "pk", None)

    def _row_value(self, row: Any, field: str) -> Any:
        """Extract a field value from a record."""
        if isinstance(row, dict):
            return row.get(field)
        return getattr(row, field, None)

    async def _find_pivot_rows(self) -> list[Any]:
        """Look up pivot rows for the current parent through the data source."""
        query = QuerySpec().with_where_eq(self.related_key_local, self.parent_id)
        result = await self._data_source.find_many(query)
        if result is None:
            return []
        return list(result.items) if hasattr(result, "items") else []

    async def _matching_pivot_rows(self, related_id: str) -> list[Any]:
        """Pivot rows linking the current parent to the given related record."""
        rows = await self._find_pivot_rows()
        return [
            row
            for row in rows
            if str(self._row_value(row, self.related_key)) == str(related_id)
        ]

    async def attach(
        self, related_id: str, pivot_data: dict[str, Any] | None = None
    ) -> None:
        """Attach a related record with optional pivot data.

        Persists a pivot row through the attached data source.

        Args:
            related_id: ID of the related record to attach.
            pivot_data: Optional values for configured pivot columns.

        Raises:
            RelationPersistenceError: When no pivot table or data
                source is configured.
        """
        self._require_persistence()
        row: dict[str, Any] = {
            self.related_key_local: self.parent_id,
            self.related_key: related_id,
        }
        if pivot_data:
            if self.pivot_columns:
                row.update(
                    {k: v for k, v in pivot_data.items() if k in self.pivot_columns}
                )
            else:
                row.update(pivot_data)
        await self._data_source.create(row)

    async def detach(self, related_id: str) -> None:
        """Detach a related record by removing its pivot rows.

        Args:
            related_id: ID of the related record to detach.

        Raises:
            RelationPersistenceError: When no pivot table or data
                source is configured.
        """
        self._require_persistence()
        rows = await self._matching_pivot_rows(related_id)
        ids = [self._row_id(row) for row in rows if self._row_id(row) is not None]
        if ids:
            await self._data_source.bulk_delete(ids)

    async def sync(
        self,
        related_ids: Sequence[str],
        pivot_data_map: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """Sync related records, detaching any not in the list and attaching new ones.

        Args:
            related_ids: IDs to keep attached.
            pivot_data_map: Optional mapping of related_id -> pivot data.

        Raises:
            RelationPersistenceError: When no pivot table or data
                source is configured.
        """
        current = await self.get_attached_ids()
        pivot_data_map = pivot_data_map or {}
        for related_id in current:
            if related_id not in related_ids:
                await self.detach(related_id)
        for related_id in related_ids:
            if related_id not in current:
                await self.attach(related_id, pivot_data_map.get(related_id))

    async def get_attached_ids(self) -> list[str]:
        """Return IDs of currently attached related records."""
        if self._data_source is None:
            return []
        rows = await self._find_pivot_rows()
        return [
            str(self._row_value(row, self.related_key))
            for row in rows
            if self._row_value(row, self.related_key) is not None
        ]

    async def get_pivot_data(self, related_id: str) -> dict[str, Any] | None:
        """Return pivot data for a single attached record."""
        if self._data_source is None:
            return None
        rows = await self._matching_pivot_rows(related_id)
        if not rows:
            return None
        row = rows[0]
        if self.pivot_columns:
            return {col: self._row_value(row, col) for col in self.pivot_columns}
        if isinstance(row, dict):
            return dict(row)
        return (
            {key: getattr(row, key) for key in vars(row) if not key.startswith("_")}
            if hasattr(row, "__dict__")
            else None
        )

    async def update_pivot(self, related_id: str, pivot_data: dict[str, Any]) -> None:
        """Update pivot data for an attached record.

        Args:
            related_id: ID of the attached related record.
            pivot_data: Values for configured pivot columns.

        Raises:
            RelationPersistenceError: When no pivot table or data
                source is configured.
        """
        self._require_persistence()
        rows = await self._matching_pivot_rows(related_id)
        if not rows:
            return
        row_id = self._row_id(rows[0])
        if row_id is None:
            return
        updates = (
            {k: v for k, v in pivot_data.items() if k in self.pivot_columns}
            if self.pivot_columns
            else dict(pivot_data)
        )
        if updates:
            await self._data_source.update(row_id, updates)

    async def render(self, request: Request, resource_name: str = "") -> str:
        items = await self.get_query()
        attached_ids = await self.get_attached_ids()
        rel_name = self.get_relationship_name()

        rows: list[Any] = []
        for item in items:
            item_id = str(getattr(item, "id", ""))
            is_attached = item_id in attached_ids
            label = str(getattr(item, "name", item_id))

            pivot_data = await self.get_pivot_data(item_id) if is_attached else None
            rows.append(
                self._build_row(
                    resource_name,
                    item_id,
                    label,
                    is_attached,
                    self._render_pivot_cells(item_id, pivot_data),
                )
            )

        header = el(
            "div",
            el(
                "h3",
                rel_name.replace("_", " ").title(),
                class_="text-lg font-medium text-foreground",
            ),
            el(
                "div",
                el(
                    "input",
                    type="text",
                    class_="px-3 py-1.5 text-sm border rounded-lg",
                    placeholder="Search...",
                    id=f"search-{rel_name}",
                    hx_trigger="keyup changed delay:300ms",
                    hx_get=f"/admin/{resource_name}/{self.parent_id}/relations/{rel_name}",
                    hx_target=f"#relation-panel-{rel_name}",
                    hx_select=".relation-panel",
                ),
                class_="flex gap-2",
            ),
            class_="flex items-center justify-between mb-4",
        )

        table = el(
            "table",
            el(
                "thead",
                el(
                    "tr",
                    el(
                        "th",
                        "Attach",
                        class_="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase",
                    ),
                    el(
                        "th",
                        "Record",
                        class_="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase",
                    ),
                    *self._pivot_header_elements(),
                    el(
                        "th",
                        "ID",
                        class_="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase",
                    ),
                ),
                class_="bg-muted dark:bg-card",
            ),
            el("tbody", *rows, class_="divide-y divide-border"),
            class_="min-w-full divide-y divide-border",
        )

        return render_to_string(
            el(
                "div",
                header,
                table,
                el(
                    "button",
                    "Save",
                    type="button",
                    class_="px-3 py-1.5 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700",
                    hx_post=f"/admin/{resource_name}/{self.parent_id}/relations/{rel_name}/sync",
                    hx_target=f"#relation-panel-{rel_name}",
                    hx_swap="outerHTML",
                ),
                class_="relation-panel p-4",
                id=f"relation-panel-{rel_name}",
            )
        )

    def _pivot_header_elements(self) -> list[Any]:
        """Return table header cell elements for the pivot columns."""
        return [
            el(
                "th",
                c.replace("_", " ").title(),
                class_="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase",
            )
            for c in self.pivot_columns
        ]

    def _render_pivot_headers(self) -> str:
        """Render the pivot column table headers as HTML."""
        return render_to_string(self._pivot_header_elements())

    def _build_row(
        self,
        resource_name: str,
        item_id: str,
        label: str,
        is_attached: bool,
        pivot_cells: list[Any],
    ) -> Any:
        """Build a single belongs-to-many row element."""
        rel_name = self.get_relationship_name()
        return el(
            "tr",
            el(
                "td",
                el(
                    "input",
                    type="checkbox",
                    class_="belongs-to-many-checkbox rounded border-border text-primary-600 focus:ring-primary-500",
                    data_related_id=item_id,
                    checked="checked" if is_attached else None,
                    hx_post=f"/admin/{resource_name}/{self.parent_id}/relations/{rel_name}/toggle",
                    hx_vals=dumps_str({"related_id": item_id}),
                    hx_target="closest tr",
                    hx_swap="outerHTML",
                ),
            ),
            el("td", label, class_="px-4 py-2 text-sm text-foreground"),
            *pivot_cells,
            el("td", item_id, class_="px-4 py-2 text-sm text-muted-foreground"),
            class_="bg-primary-50 dark:bg-primary-900/20" if is_attached else None,
        )

    def _render_pivot_cells(
        self, related_id: str, pivot_data: dict[str, Any] | None
    ) -> list[Any]:
        """Return pivot cell elements for a single related record."""
        if not self.pivot_columns:
            return []
        cells: list[Any] = []
        for col in self.pivot_columns:
            value = (pivot_data or {}).get(col, "")
            cells.append(
                el(
                    "td",
                    el(
                        "input",
                        type="text",
                        class_="px-2 py-1 text-sm border rounded w-full",
                        value=value,
                        name=f"pivot_{col}_{related_id}",
                        hx_post=f"/admin/{self.parent_id}/relations/{self.get_relationship_name()}/pivot/{related_id}",
                        hx_trigger="change",
                        hx_swap="none",
                    ),
                    class_="px-4 py-2",
                )
            )
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
        return HTMLResponse(
            render_to_string(
                self._build_row(
                    resource_name,
                    related_id,
                    label,
                    is_attached,
                    self._render_pivot_cells(related_id, pivot_data),
                )
            )
        )
