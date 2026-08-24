"""Shared scaffolding for admin UI-control scenario tests.

Provides ``FakeRecord``/``FakeDataSource``, ``_make_records``, and a
``ScenarioController`` wired with searchable, sortable, filterable,
selectable, soft-deletable, action-enabled columns. Imported by the
forms and tables scenario suites.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from lexigram.admin.controllers.resource import ResourceController, ResourceMeta
from lexigram.admin.data.data_source import QueryResult
from lexigram.admin.ui.filters import SelectFilter
from lexigram.admin.ui.organisms.data_table import DataTable
from lexigram.admin.ui.organisms.sidebar import SidebarItem, SidebarSection
from lexigram.admin.ui.templates.shell import AdminShell
from lexigram.ui import el, render_to_string
from lexigram.ui.actions import Action, BulkAction
from lexigram.ui.columns.types import BadgeColumn, DateColumn, TextColumn

# ── Helpers ────────────────────────────────────────────────────────────────


@dataclass
class FakeRecord:
    id: int
    name: str
    email: str
    status: str = "active"
    created_at: str = ""


def _make_records(count: int = 25) -> list[FakeRecord]:
    now = datetime.now(UTC).isoformat()
    statuses = ["active", "archived", "pending"]
    return [
        FakeRecord(
            id=i,
            name=f"User {i}",
            email=f"user{i}@example.com",
            status=statuses[i % 3],
            created_at=now,
        )
        for i in range(1, count + 1)
    ]


# ── Fake Data Source ───────────────────────────────────────────────────────


class FakeDataSource:
    """In-memory IDataSource for scenario testing."""

    def __init__(self, records: list[FakeRecord] | None = None) -> None:
        self._records: dict[int, FakeRecord] = {
            r.id: r for r in (records or _make_records(25))
        }
        self._next_id = 1000

    async def find_one(self, item_id: Any) -> FakeRecord | None:
        return self._records.get(int(item_id) if item_id else None)

    async def find_many(self, query: Any) -> QueryResult[FakeRecord]:
        items = list(self._records.values())

        # Search
        if query.search and query.search_fields:
            term = query.search.lower()
            items = [
                i
                for i in items
                if any(
                    term in str(getattr(i, f, "")).lower() for f in query.search_fields
                )
            ]

        # Filters
        for cond in getattr(query, "where", []):
            field = cond.field
            op = (
                cond.operator.value
                if hasattr(cond.operator, "value")
                else cond.operator
            )
            val = cond.value
            if op == "eq":
                items = [i for i in items if str(getattr(i, field, "")) == str(val)]
            elif op == "in":
                items = [i for i in items if str(getattr(i, field, "")) in val]

        # Sort
        sort_by = query.sort_by or "id"
        reverse = (query.sort_order or "asc") == "desc"
        items.sort(key=lambda i: getattr(i, sort_by, "") or "", reverse=reverse)

        # Pagination
        total = len(items)
        page = query.page or 1
        per_page = query.per_page or 20
        start = (page - 1) * per_page
        end = start + per_page
        paged = items[start:end]

        return QueryResult(
            items=paged,
            total=total,
            page=page,
            per_page=per_page,
            has_next=end < total,
            has_prev=page > 1,
        )

    async def count(self, query: Any) -> int:
        result = await self.find_many(query)
        return result.total

    async def create(self, data: dict[str, Any]) -> FakeRecord:
        rid = self._next_id
        self._next_id += 1
        rec = FakeRecord(
            id=rid,
            name=data.get("name", "New"),
            email=data.get("email", "new@example.com"),
            status=data.get("status", "active"),
            created_at=datetime.now(UTC).isoformat(),
        )
        self._records[rid] = rec
        return rec

    async def update(self, item_id: Any, data: dict[str, Any]) -> FakeRecord | None:
        rec = self._records.get(int(item_id))
        if rec is None:
            return None
        for key, val in data.items():
            if hasattr(rec, key):
                setattr(rec, key, val)
        return rec

    async def delete(self, item_id: Any) -> bool:
        return self._records.pop(int(item_id), None) is not None

    async def bulk_delete(self, ids: list[str]) -> int:
        count = 0
        for id_ in ids:
            if self._records.pop(int(id_), None) is not None:
                count += 1
        return count

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[FakeRecord]:
        created = []
        for data in items:
            created.append(await self.create(data))
        return created

    async def bulk_update(self, ids: list[str], data: dict[str, Any]) -> int:
        count = 0
        for id_ in ids:
            rec = self._records.get(int(id_))
            if rec is not None:
                for key, val in data.items():
                    if hasattr(rec, key):
                        setattr(rec, key, val)
                count += 1
        return count


# ── Scenario Controller ────────────────────────────────────────────────────

COLUMNS = [
    TextColumn("name").sortable(),
    TextColumn("email").sortable(),
    BadgeColumn("status"),
    DateColumn("created_at").sortable(),
]

FILTERS = [
    SelectFilter(
        "status",
        options={"active": "Active", "archived": "Archived", "pending": "Pending"},
    ),
]

ACTIONS = [
    Action("edit", label="Edit"),
    Action("delete", label="Delete"),
]

BULK_ACTIONS = [
    BulkAction("delete", label="Delete selected"),
]


class ScenarioController(ResourceController[FakeRecord]):
    """Concrete controller for scenario testing with rich rendering."""

    meta = ResourceMeta(
        name="item",
        label="Item",
        label_plural="Items",
        prefix="",
        per_page=10,
        searchable_fields=["name", "email"],
        default_sort="id",
        default_sort_order="asc",
        enable_create=True,
        enable_edit=True,
        enable_delete=True,
        enable_bulk_actions=True,
    )
    soft_delete_enabled = True

    def __init__(self, data_source: FakeDataSource | None = None) -> None:
        super().__init__(data_source=data_source)

    def get_data_source(self) -> FakeDataSource:
        if self._data_source is None:
            raise NotImplementedError
        return self._data_source

    # ── List rendering ──────────────────────────────────────────────────

    def render_list(
        self,
        ctx: Any,
        result: QueryResult[FakeRecord],
        state: Any,
    ) -> str:
        """Full page with sidebar + table."""
        data_table = self._build_data_table(result, state)
        table_html = render_to_string(data_table)

        nav_items = [
            {"label": "Dashboard", "href": "/admin", "icon": "chart-bar"},
            SidebarSection(
                title="Content",
                items=[
                    SidebarItem(label="Items", href="/item", icon="box"),
                    SidebarItem(label="Users", href="/admin/users", icon="users"),
                ],
            ),
            SidebarSection(
                title="System",
                items=[
                    SidebarItem(label="Settings", href="/admin/settings", icon="cog"),
                ],
            ),
        ]

        shell = AdminShell(
            content=el(
                "div", el("h1", "Items", class_="text-2xl font-bold mb-4"), table_html
            ),
            title="Items",
            nav_items=nav_items,
            user={"name": "Admin"},
        )
        return render_to_string(shell)

    def render_list_partial(
        self,
        ctx: Any,
        result: QueryResult[FakeRecord],
        state: Any,
    ) -> str:
        """HTMX partial — just the table."""
        data_table = self._build_data_table(result, state)
        return render_to_string(data_table)

    def _build_data_table(
        self,
        result: QueryResult[FakeRecord],
        state: Any,
    ) -> DataTable:
        """Build DataTable from query result and URL state."""
        records = []
        for r in result.items:
            rec = {
                "id": str(r.id),
                "name": r.name,
                "email": r.email,
                "status": r.status,
                "created_at": r.created_at,
            }
            records.append(rec)

        dt = DataTable(
            columns=COLUMNS,
            data=records,
            page=result.page,
            per_page=result.per_page,
            total=result.total,
            sort_by=getattr(state, "sort", None),
            sort_order=getattr(state, "order", "asc"),
            actions=ACTIONS,
            bulk_actions=BULK_ACTIONS,
            filter_options=FILTERS,
            resource_prefix="/item",
            resource_name="item",
            # Matches the route's scope
            filters={
                "search": getattr(state, "search", ""),
                **(getattr(state, "filters", {}) or {}),
            },
        )
        return dt

    # ── Detail rendering ────────────────────────────────────────────────

    def render_detail_partial(self, ctx: Any, item: FakeRecord) -> str:
        return render_to_string(
            el(
                "div",
                el("h2", item.name, class_="text-xl font-bold"),
                el("p", f"Email: {item.email}"),
                el("p", f"Status: {item.status}"),
                class_="p-4",
            )
        )

    def render_form_partial(
        self,
        ctx: Any,
        item: FakeRecord | None,
        data: dict[str, Any] | None = None,
        errors: dict[str, list[str]] | None = None,
    ) -> str:
        name_val = (data or {}).get("name", item.name if item else "")
        email_val = (data or {}).get("email", item.email if item else "")
        return render_to_string(
            el(
                "form",
                el("label", "Name"),
                el("input", name="name", value=name_val, type="text"),
                el("label", "Email"),
                el("input", name="email", value=email_val, type="email"),
                el("button", "Save", type="submit"),
                method="POST",
            )
        )


# ── App / Client Fixtures ──────────────────────────────────────────────────

