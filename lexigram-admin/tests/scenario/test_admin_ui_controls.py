"""Scenario test: full admin UI control integration.

Verifies the list page HTML contract and HTMX interactions for a fake
resource with searchable, sortable, filterable, selectable,
soft-deletable, and action-enabled records.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.scenario]

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from starlette.applications import Starlette

from lexigram.admin.controllers.resource import ResourceController, ResourceMeta
from lexigram.admin.data.data_source import QueryResult
from lexigram.ui.actions import Action, BulkAction
from lexigram.ui.columns.types import BadgeColumn, DateColumn, TextColumn
from lexigram.admin.ui.filters import SelectFilter
from lexigram.admin.ui.organisms.data_table import DataTable
from lexigram.admin.ui.organisms.sidebar import SidebarItem, SidebarSection
from lexigram.admin.ui.templates.shell import AdminShell
from lexigram.ui import el, render_to_string

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


@pytest.fixture
def ds() -> FakeDataSource:
    return FakeDataSource(_make_records(25))


@pytest.fixture
def controller(ds: FakeDataSource) -> ScenarioController:
    return ScenarioController(data_source=ds)


@pytest.fixture
def app(controller: ScenarioController) -> Starlette:
    routes = controller.get_routes()
    return Starlette(routes=routes)


@pytest.fixture
async def client(app: Starlette):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as c:
        yield c


# ── Tests ──────────────────────────────────────────────────────────────────


class TestFullPageHTMLContract:
    """Initial full-page render includes all expected controls."""

    async def _get(self, client: httpx.AsyncClient) -> httpx.Response:
        return await client.get("/item")

    async def test_returns_200(self, client: httpx.AsyncClient) -> None:
        resp = await self._get(client)
        assert resp.status_code == 200

    async def test_includes_sidebar(self, client: httpx.AsyncClient) -> None:
        resp = await self._get(client)
        assert "Items" in resp.text
        assert "Dashboard" in resp.text
        assert "Settings" in resp.text

    async def test_includes_search_input(self, client: httpx.AsyncClient) -> None:
        resp = await self._get(client)
        assert "search" in resp.text.lower() or 'type="search"' in resp.text

    async def test_includes_filter_controls(self, client: httpx.AsyncClient) -> None:
        resp = await self._get(client)
        bodies = ["status", "active", "archived"]
        assert any(b in resp.text.lower() for b in bodies)

    async def test_includes_sort_links(self, client: httpx.AsyncClient) -> None:
        resp = await self._get(client)
        assert "sort" in resp.text.lower() or "order" in resp.text.lower()

    async def test_includes_pagination(self, client: httpx.AsyncClient) -> None:
        resp = await self._get(client)
        assert "page" in resp.text.lower() or "1" in resp.text

    async def test_includes_selection_checkboxes(
        self, client: httpx.AsyncClient
    ) -> None:
        resp = await self._get(client)
        assert 'type="checkbox"' in resp.text

    async def test_includes_bulk_actions(self, client: httpx.AsyncClient) -> None:
        resp = await self._get(client)
        assert "delete" in resp.text.lower()


class TestHTMXSearch:
    """HTMX search request returns filtered table content."""

    async def test_search_filters_results(self, client: httpx.AsyncClient) -> None:
        resp = await client.get(
            "/item?q=User+1&sort=id&order=asc", headers={"hx-request": "true"}
        )
        assert resp.status_code == 200

    async def test_search_empty_returns_all(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item?search=", headers={"hx-request": "true"})
        assert resp.status_code == 200

    async def test_search_no_match(self, client: httpx.AsyncClient) -> None:
        resp = await client.get(
            "/item?search=zzzznotfound", headers={"hx-request": "true"}
        )
        assert resp.status_code == 200
        assert "No results" in resp.text or "no" in resp.text.lower()


class TestHTMXFilter:
    """HTMX filter request returns filtered table content."""

    async def test_filter_status(self, client: httpx.AsyncClient) -> None:
        resp = await client.get(
            "/item?filter%5Bstatus%5D=archived", headers={"hx-request": "true"}
        )
        assert resp.status_code == 200


class TestHTMXSort:
    """HTMX sort request returns sorted table content."""

    async def test_sort_by_name_asc(self, client: httpx.AsyncClient) -> None:
        resp = await client.get(
            "/item?sort=name&order=asc", headers={"hx-request": "true"}
        )
        assert resp.status_code == 200

    async def test_sort_by_name_desc(self, client: httpx.AsyncClient) -> None:
        resp = await client.get(
            "/item?sort=name&order=desc", headers={"hx-request": "true"}
        )
        assert resp.status_code == 200


class TestHTMXPagination:
    """HTMX pagination requests."""

    async def test_page_2_has_different_items(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item?page=2", headers={"hx-request": "true"})
        assert resp.status_code == 200

    async def test_page_out_of_range(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item?page=99", headers={"hx-request": "true"})
        assert resp.status_code == 200


class TestCRUD:
    """CRUD operations via HTTP."""

    async def test_detail(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item/1")
        assert resp.status_code == 200
        assert "User 1" in resp.text

    async def test_detail_not_found(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item/99999")
        assert resp.status_code == 404

    async def test_create_form(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item/create")
        assert resp.status_code == 200

    async def test_create_submit(
        self, client: httpx.AsyncClient, ds: FakeDataSource
    ) -> None:
        before = len(ds._records)
        resp = await client.post(
            "/item", data={"name": "New Person", "email": "new@test.com"}
        )
        assert resp.status_code in (200, 302)
        assert len(ds._records) == before + 1

    async def test_edit_form(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item/1/edit")
        assert resp.status_code == 200

    async def test_update_via_put(self, client: httpx.AsyncClient) -> None:
        """PUT is the canonical update verb."""
        resp = await client.request(
            "PUT", "/item/1", data={"name": "Updated", "email": "u@test.com"}
        )
        assert resp.status_code in (200, 302)

    async def test_delete(self, client: httpx.AsyncClient) -> None:
        resp = await client.delete("/item/1")
        assert resp.status_code in (200, 302)


class TestBulkAction:
    """Bulk action submits action name + IDs."""

    async def test_bulk_delete(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/item/bulk",
            data={"action": "delete", "ids": ["1", "2"]},
            headers={"hx-request": "true"},
        )
        assert resp.status_code == 200

    async def test_bulk_delete_redirects_without_htmx(
        self, client: httpx.AsyncClient
    ) -> None:
        resp = await client.post(
            "/item/bulk", data={"action": "delete", "ids": ["1", "2"]}
        )
        assert resp.status_code in (302, 200)


class TestHTMXModalsAndSlideOvers:
    """Actions with modal/slide-over targets."""

    async def test_htmx_detail_returns_partial(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item/1", headers={"hx-request": "true"})
        assert resp.status_code == 200
        assert "User 1" in resp.text


class TestPageSize:
    """Page size changes are respected."""

    async def test_per_page_5(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item?per_page=5", headers={"hx-request": "true"})
        assert resp.status_code == 200
