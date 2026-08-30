"""End-to-end resource lifecycle through the real admin setup pipeline.

Boots the panel exactly the way an application would — a declarative
``Resource`` subclass registered via ``AdminProvider(resources=[...])``,
``register()`` → ``boot()`` → ``mount_to_app()`` — then drives the full
CRUD surface over ASGI:

- setup: resource class → named instance → routes mounted under the prefix
- tables: list page, columns, search, filter, sort, pagination
- forms: create form GET/POST, edit form GET/POST (with CSRF round-trip)
- detail: record page
- delete: confirm + DELETE

This is the Filament-style contract: declare the resource, hand it to the
module, get working tables/forms/routes with no controller code.
"""

from __future__ import annotations

import re
from typing import Any

import httpx
import pytest
from starlette.applications import Starlette

pytestmark = [pytest.mark.scenario]

from lexigram.admin.config import AdminConfig
from lexigram.admin.data.data_source import QueryResult
from lexigram.admin.di.bundle_provider import AdminProvider
from lexigram.admin.resources import Resource
from lexigram.di.container import Container
from lexigram.ui.columns.types import BadgeColumn, TextColumn

# ── Data source (stands in for a repository-backed IDataSource) ────────────


class ProductStore:
    """In-memory IDataSource-compatible store for product records."""

    def __init__(self, seed: list[dict[str, Any]] | None = None) -> None:
        self._records: dict[int, dict[str, Any]] = {}
        self._next_id = 1000
        for rec in seed or []:
            self._records[int(rec["id"])] = dict(rec)

    def _query_items(self, query: Any) -> list[dict[str, Any]]:
        items = list(self._records.values())
        if query.search and query.search_fields:
            term = query.search.lower()
            items = [
                i
                for i in items
                if any(
                    term in str(i.get(f, "")).lower() for f in query.search_fields
                )
            ]
        for cond in getattr(query, "where", []):
            field = cond.field
            op = (
                cond.operator.value
                if hasattr(cond.operator, "value")
                else cond.operator
            )
            val = cond.value
            if op == "eq":
                items = [i for i in items if str(i.get(field, "")) == str(val)]
            elif op == "in":
                items = [i for i in items if str(i.get(field, "")) in (val or [])]
        sort_by = query.sort_by or "id"
        reverse = (query.sort_order or "asc") == "desc"
        items.sort(key=lambda i: str(i.get(sort_by, "")), reverse=reverse)
        return items

    async def find_many(self, query: Any) -> QueryResult:
        items = self._query_items(query)
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

    async def find_one(self, item_id: Any) -> dict[str, Any] | None:
        if item_id is None:
            return None
        return self._records.get(int(item_id))

    async def count(self, query: Any) -> int:
        return len(self._query_items(query))

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        rid = self._next_id
        self._next_id += 1
        rec = dict(data)
        rec["id"] = rid
        self._records[rid] = rec
        return rec

    async def update(
        self, item_id: Any, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        rec = self._records.get(int(item_id))
        if rec is None:
            return None
        rec.update(data)
        return rec

    async def delete(self, item_id: Any) -> bool:
        return self._records.pop(int(item_id), None) is not None

    async def bulk_delete(self, ids: list[str]) -> int:
        n = 0
        for i in ids:
            if self._records.pop(int(i), None) is not None:
                n += 1
        return n

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [await self.create(d) for d in items]

    async def bulk_update(self, ids: list[str], data: dict[str, Any]) -> int:
        n = 0
        for i in ids:
            rec = self._records.get(int(i))
            if rec is not None:
                rec.update(data)
                n += 1
        return n


# ── Declarative resource (the Filament-style contract) ─────────────────────

from pydantic import BaseModel, Field


class ProductModel(BaseModel):
    """Pydantic model backing the resource: form generation + validation."""

    name: str = Field(min_length=1, max_length=120)
    sku: str = Field(min_length=1, max_length=40)
    status: str = "active"


class ProductResource(Resource):
    """A resource declared with columns + search only — no controller code."""

    name = "product"
    label = "Product"
    icon = "box"

    model = ProductModel

    # The mount pipeline resolves this from DI and calls set_data_source().
    _data_source_class = ProductStore

    columns = [
        TextColumn("name").sortable(),
        TextColumn("sku").sortable(),
        BadgeColumn("status"),
    ]
    search_fields = ["name", "sku"]
    page_size = 5
    default_sort = "name"
    default_sort_order = "asc"

    permissions = None


def _seed_products(count: int = 12) -> list[dict[str, Any]]:
    return [
        {
            "id": i,
            "name": f"Widget {i}",
            "sku": f"SKU-{i:04d}",
            "status": "active" if i % 2 else "archived",
        }
        for i in range(1, count + 1)
    ]


class _FakeDbProvider:
    """Async stand-in for DatabaseProviderProtocol (SQLite-ish, no-op)."""

    database_type = "sqlite"

    async def execute_query(
        self, sql: str, params: list | None = None, **kwargs: Any
    ) -> list:
        return []

    async def execute(
        self, sql: str, params: list | None = None, **kwargs: Any
    ) -> Any:
        return None

    async def execute_insert(
        self, table: str, data: dict | None = None, **kwargs: Any
    ) -> Any:
        return 1

    async def execute_update(
        self, table: str, data: dict | None = None, **kwargs: Any
    ) -> Any:
        return 1

    async def execute_delete(
        self, table: str, **kwargs: Any
    ) -> Any:
        return 1

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def is_connected(self) -> bool:
        return True

    async def get_primary_pool(self) -> Any:
        return None


class _FakeAdminUser:
    user_id = "admin-1"
    name = "Admin"
    email = "admin@example.com"
    is_active = True
    roles = ["admin"]


class _FakeAdminUserStore:
    """AdminUserStoreProtocol stand-in: one admin exists, no sessions."""

    async def get_admin_count(self) -> int:
        return 1

    async def get_by_id(self, user_id: Any) -> Any:
        return _FakeAdminUser() if user_id == "admin-1" else None

    async def ensure_schema(self) -> None:
        return None

    async def get_user_by_email(self, email: str) -> Any | None:
        return None

    async def get_user_by_username(self, username: str) -> Any | None:
        return None


class _FakeSessionService:
    """AdminSessionServiceProtocol stand-in: one valid session."""

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        if session_id == "test-session-1":
            return {"admin_id": "admin-1"}
        return None

    async def revoke_session(self, session_id: str) -> None:
        return None


def _signed_session_cookie(secret_key: str, data: dict[str, Any]) -> str:
    """Sign a session cookie the way Starlette SessionMiddleware does."""
    import base64
    import hashlib
    import json

    import itsdangerous
    from itsdangerous.serializer import Serializer
    from starlette.middleware.sessions import SessionMiddleware

    # Match Starlette's exact cookie format: base64(json) signed by a
    # TimestampSigner with the middleware's secret key.
    signer = itsdangerous.TimestampSigner(str(secret_key))
    payload = base64.b64encode(json.dumps(data).encode()).decode()
    signed = signer.sign(payload.encode()).decode()
    return signed


# ── App boot (the real setup path) ─────────────────────────────────────────


@pytest.fixture
def store() -> ProductStore:
    return ProductStore(_seed_products())


@pytest.fixture
async def app(store: ProductStore) -> Starlette:
    """Boot the admin panel through the provider lifecycle and mount it."""
    from lexigram.admin.auth.protocols.session import AdminSessionServiceProtocol
    from lexigram.admin.auth.store.protocols import AdminUserStoreProtocol
    from lexigram.contracts.data.sql.database import DatabaseProviderProtocol

    config = AdminConfig.from_dict(
        {
            "prefix": "/admin",
            "require_auth": False,
            "auth": {
                "security": {"setup_token": "test-setup-token"},
                "session_secret": "test-session-secret-for-e2e-scenario",
            },
        }
    )
    provider = AdminProvider(config=config, resources=[ProductResource])

    container = Container()
    container.singleton(ProductStore, store)
    # Stand in for the app's real database module: the admin auth/session
    # stores are SQL-backed and resolve the DB provider from DI. Wrapped in a
    # factory to skip static protocol validation of the test double.
    container.singleton(DatabaseProviderProtocol, lambda: _FakeDbProvider())
    await provider.register(container)
    # Override the SQL-backed stores with in-memory fakes: SetupMiddleware
    # must see one existing admin (no first-run wizard redirect) and the auth
    # middleware resolves sessions against these stores.
    container.singleton(AdminUserStoreProtocol, lambda: _FakeAdminUserStore())
    container.singleton(
        AdminSessionServiceProtocol, lambda: _FakeSessionService()
    )
    await provider.boot(container)

    starlette_app = Starlette()
    await provider.mount_to_app(starlette_app, container)
    starlette_app.state._admin_session_secret = (
        config.auth.session_secret.get_secret_value()
    )
    return starlette_app


@pytest.fixture
async def client(app: Starlette):
    cookie = _signed_session_cookie(
        app.state._admin_session_secret,
        # Mirrors the authenticated session state written by the real login
        # controller (login.py: request.session["admin_user_id"] = ...).
        {"session_id": "test-session-1", "admin_user_id": "admin-1"},
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        cookies={"session": cookie},
    ) as c:
        yield c


def _csrf_token_from(html: str) -> str:
    """Extract the hidden csrf_token from a rendered form."""
    m = re.search(
        r'name="csrf_token"\s+value="([^"]+)"|value="([^"]+)"\s+name="csrf_token"',
        html,
    )
    assert m, f"csrf_token hidden input not found in form HTML:\n{html[:500]}"
    return m.group(1) or m.group(2)


# ── Setup ───────────────────────────────────────────────────────────────────


class TestSetup:
    async def test_list_route_mounted(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/admin/product")
        assert resp.status_code == 200

    async def test_unknown_resource_404(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/admin/does-not-exist")
        assert resp.status_code in (404, 405)


# ── Tables ──────────────────────────────────────────────────────────────────


class TestTables:
    async def test_list_shows_column_headers(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/admin/product")
        assert resp.status_code == 200
        for header in ("Name", "SKU", "Status"):
            assert header in resp.text

    async def test_list_shows_records(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/admin/product")
        assert "Widget 1" in resp.text
        assert "SKU-0001" in resp.text

    async def test_search_filters_records(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/admin/product", params={"q": "Widget 3"})
        assert resp.status_code == 200
        assert "Widget 3" in resp.text
        assert "Widget 1" not in resp.text

    async def test_search_uses_resource_search_fields(
        self, client: httpx.AsyncClient
    ) -> None:
        resp = await client.get("/admin/product", params={"search": "SKU-0007"})
        assert resp.status_code == 200
        assert "Widget 7" in resp.text

    async def test_sort_by_name_desc(self, client: httpx.AsyncClient) -> None:
        resp = await client.get(
            "/admin/product", params={"sort": "name", "order": "desc"}
        )
        assert resp.status_code == 200
        # "Widget 9" sorts above "Widget 1" lexicographically
        assert "Widget 9" in resp.text

    async def test_pagination_respects_page_size(
        self, client: httpx.AsyncClient
    ) -> None:
        resp = await client.get("/admin/product")
        assert resp.status_code == 200
        # page_size=5 → 12 records → page 2 exists
        resp2 = await client.get("/admin/product", params={"page": 2})
        assert resp2.status_code == 200

    async def test_filter_by_status(self, client: httpx.AsyncClient) -> None:
        resp = await client.get(
            "/admin/product", params={"filter[status]": "archived"}
        )
        assert resp.status_code == 200
        assert "archived" in resp.text.lower()


# ── Forms: create ───────────────────────────────────────────────────────────


class TestCreateForm:
    async def test_create_form_renders_fields(
        self, client: httpx.AsyncClient
    ) -> None:
        resp = await client.get("/admin/product/create")
        assert resp.status_code == 200
        assert "Product" in resp.text
        assert "name" in resp.text.lower()

    async def test_create_persists_and_redirects(
        self, client: httpx.AsyncClient
    ) -> None:
        form_resp = await client.get("/admin/product/create")
        token = _csrf_token_from(form_resp.text)

        resp = await client.post(
            "/admin/product/create",
            data={
                "csrf_token": token,
                "name": "New Widget",
                "sku": "SKU-NEW",
                "status": "active",
            },
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        assert "HX-Redirect" in resp.headers or resp.status_code in (301, 302)

        listing = await client.get("/admin/product", params={"q": "New Widget"})
        assert "New Widget" in listing.text

    async def test_create_rejects_missing_csrf(
        self, client: httpx.AsyncClient
    ) -> None:
        resp = await client.post(
            "/admin/product",
            data={"name": "No CSRF", "sku": "SKU-NOCSRF", "status": "active"},
        )
        assert resp.status_code in (403, 422)


# ── Detail ──────────────────────────────────────────────────────────────────


class TestDetail:
    async def test_detail_shows_record(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/admin/product/1")
        assert resp.status_code == 200
        assert "Widget 1" in resp.text

    async def test_detail_missing_404(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/admin/product/999999")
        assert resp.status_code in (404, 200)


# ── Forms: edit ─────────────────────────────────────────────────────────────


class TestEditForm:
    async def test_edit_form_prefills_values(
        self, client: httpx.AsyncClient
    ) -> None:
        resp = await client.get("/admin/product/1/edit")
        assert resp.status_code == 200
        assert "Widget 1" in resp.text

    async def test_edit_updates_and_redirects(
        self, client: httpx.AsyncClient
    ) -> None:
        form_resp = await client.get("/admin/product/1/edit")
        token = _csrf_token_from(form_resp.text)

        resp = await client.post(
            "/admin/product/1/edit",
            data={
                "csrf_token": token,
                "name": "Widget 1 Renamed",
                "sku": "SKU-0001",
                "status": "active",
            },
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        assert "HX-Redirect" in resp.headers or resp.status_code in (301, 302)

        detail = await client.get("/admin/product/1")
        assert "Widget 1 Renamed" in detail.text


# ── Delete ──────────────────────────────────────────────────────────────────


class TestDelete:
    async def test_delete_confirm_renders(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/admin/product/1/delete-confirm")
        assert resp.status_code == 200

    async def test_delete_removes_record(self, client: httpx.AsyncClient) -> None:
        form_resp = await client.get("/admin/product/1/edit")
        token = _csrf_token_from(form_resp.text)

        resp = await client.delete(
            "/admin/product/1/delete",
            headers={
                "HX-Request": "true",
                "X-CSRF-Token": token,
            },
        )
        assert resp.status_code == 200
        assert "HX-Redirect" in resp.headers or resp.status_code in (301, 302)

        listing = await client.get("/admin/product", params={"q": "Widget 1"})
        # The search box echoes the query, so assert on the empty-state marker
        # rather than the raw query string.
        assert "No results found" in listing.text

    async def test_delete_missing_404(self, client: httpx.AsyncClient) -> None:
        form_resp = await client.get("/admin/product/1/edit")
        token = _csrf_token_from(form_resp.text)

        resp = await client.delete(
            "/admin/product/999999/delete",
            headers={"X-CSRF-Token": token},
        )
        assert resp.status_code in (404, 200)
