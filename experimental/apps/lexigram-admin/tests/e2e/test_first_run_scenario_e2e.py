"""First-run scenario: the complete out-of-the-box operator journey.

Boots a REAL admin application via ``bootstrap.create_app()`` — real SQL
stores against a temporary SQLite database, default security settings
(email verification enforcement ON, no mailer) — and walks the entire
first-contact flow over HTTP:

    fresh DB → setup wizard → login → dashboard → resource list
    → create → edit → logout

This single scenario guards the first-run regressions fixed on 2026-09-01
(docs/09-01-2026/01-bug-audit-and-fixes.md):

- B1: super admin must not be 403'd on resource routes / empty sidebar
- B2: sidebar renders resource links for the super admin
- B3: first admin auto-verified at setup (no mailer configured)
- B4: exactly one ``<title>`` per page
- B5: ``create_app()`` returns a mounted, working application
- B6: no third-party CDN references in served pages
- B7: no raw ``LEX_ERR`` chains in user-facing pages/redirects
- B8: setup truthfully reports success on drivers without INSERT row counts
"""

from __future__ import annotations

import re
from typing import Any

import httpx
import pytest
from pydantic import BaseModel, Field

from lexigram.admin.actions.standard.header import CreateAction
from lexigram.admin.actions.standard.row import DeleteAction, EditAction
from lexigram.admin.config import AdminConfig
from lexigram.admin.data.data_source import QueryResult
from lexigram.admin.resources import Resource
from lexigram.di.container import Container
from lexigram.sql.di.provider import DatabaseProvider
from lexigram.ui.columns.types import TextColumn

SETUP_TOKEN = "e2e-first-run-token"
ADMIN_EMAIL = "operator@example.test"
ADMIN_NAME = "First Operator"
ADMIN_PASSWORD = "Kq8!wRt5#Zn2mV7c"  # must not contain the email local-part


# ── Minimal in-memory resource ──────────────────────────────────────────────


class GadgetStore:
    """IDataSource-compatible in-memory store."""

    def __init__(self, seed: list[dict[str, Any]] | None = None) -> None:
        self._records: dict[int, dict[str, Any]] = {}
        self._next_id = 1
        for rec in seed or []:
            rid = int(rec["id"])
            self._records[rid] = dict(rec)
            self._next_id = max(self._next_id, rid + 1)

    def _items(self, query: Any) -> list[dict[str, Any]]:
        items = list(self._records.values())
        search = getattr(query, "search", None)
        fields = getattr(query, "search_fields", None)
        if search and fields:
            term = search.lower()
            items = [
                i
                for i in items
                if any(term in str(i.get(f, "")).lower() for f in fields)
            ]
        sort_by = getattr(query, "sort_by", None) or "id"
        reverse = (getattr(query, "sort_order", None) or "asc") == "desc"
        items.sort(key=lambda i: (i.get(sort_by) is None, str(i.get(sort_by))))
        if reverse:
            items.reverse()
        return items

    async def find_many(self, query: Any) -> QueryResult:
        items = self._items(query)
        total = len(items)
        page = getattr(query, "page", 1) or 1
        per_page = getattr(query, "per_page", 20) or 20
        start = (page - 1) * per_page
        paged = items[start : start + per_page]
        return QueryResult(
            items=paged,
            total=total,
            page=page,
            per_page=per_page,
            has_next=start + per_page < total,
            has_prev=page > 1,
        )

    async def find_one(self, item_id: Any) -> dict[str, Any] | None:
        try:
            return self._records.get(int(item_id))
        except (TypeError, ValueError):
            return None

    async def count(self, query: Any) -> int:
        return len(self._items(query))

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        rid = self._next_id
        self._next_id += 1
        rec = {**data, "id": rid}
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

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [await self.create(d) for d in items]

    async def bulk_update(self, ids: list[Any], data: dict[str, Any]) -> int:
        return sum(
            1 for i in ids if (await self.update(i, data)) is not None
        )

    async def bulk_delete(self, ids: list[Any]) -> int:
        return sum(1 for i in ids if await self.delete(i))


class GadgetModel(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    sku: str = Field(min_length=1, max_length=40)


class GadgetResource(Resource):
    name = "gadgets"
    label = "Gadgets"
    icon = "box"
    model = GadgetModel
    _data_source_class = GadgetStore

    columns = [TextColumn("name").sortable(), TextColumn("sku").sortable()]
    search_fields = ["name", "sku"]
    page_size = 10
    default_sort = "name"
    actions = [EditAction(), DeleteAction()]
    header_actions = [CreateAction()]
    permissions = None


# ── Helpers ─────────────────────────────────────────────────────────────────


def _csrf_token_from(html: str) -> str:
    m = re.search(
        r'name="csrf_token"\s+value="([^"]+)"|value="([^"]+)"\s+name="csrf_token"',
        html,
    )
    assert m, f"csrf_token hidden input not found:\n{html[:500]}"
    return m.group(1) or m.group(2)


def _assert_page_hygiene(html: str, *, context: str) -> None:
    """Shared page-quality assertions (B4, B6, B7)."""
    assert html.count("<title>") == 1, f"{context}: expected exactly one <title>"
    assert "unpkg.com" not in html, f"{context}: third-party CDN reference"
    assert "cdn.jsdelivr" not in html, f"{context}: third-party CDN reference"
    assert "LEX_ERR" not in html, f"{context}: raw framework error leaked"


# ── App boot: the real thing ────────────────────────────────────────────────


@pytest.fixture
async def app(tmp_path):
    """A fully mounted admin app on real SQL stores (temp SQLite)."""
    from lexigram.admin.bootstrap import create_app

    container = Container()
    db = DatabaseProvider(config=f"sqlite+aiosqlite:///{tmp_path}/first_run.db")
    await db.register(container)
    await db.boot(container)
    container.singleton(
        GadgetStore,
        GadgetStore([{"id": 1, "name": "Seed Gadget", "sku": "SKU-0001"}]),
    )

    config = AdminConfig.from_dict(
        {
            "prefix": "/admin",
            "title": "First Run E2E",
            "auth": {
                "session_secret": "e2e-first-run-session-secret",
                "security": {"setup_token": SETUP_TOKEN},
                # NOTE: email verification enforcement stays at its default
                # (ON) and no mailer is configured — exactly the fresh-install
                # situation that used to brick the first admin (B3).
            },
        }
    )

    return await create_app(
        resources=[GadgetResource],
        config=config,
        container=container,
    )


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as c:
        yield c


# ── The scenario ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_first_run_operator_journey(client: httpx.AsyncClient) -> None:
    # 1. Fresh install: any admin URL redirects to the setup wizard.
    resp = await client.get("/admin/gadgets")
    assert resp.status_code in (302, 307)
    assert resp.headers["location"].endswith("/setup")

    # 2. Setup wizard renders (single title, no CDN, no raw errors).
    resp = await client.get("/admin/setup")
    assert resp.status_code == 200
    _assert_page_hygiene(resp.text, context="setup form")
    csrf = _csrf_token_from(resp.text)

    # 3. Create the first admin — must be reported as SUCCESS (B8: no false
    #    "Setup is already complete" on drivers without INSERT row counts).
    resp = await client.post(
        "/admin/setup",
        data={
            "csrf_token": csrf,
            "setup_token": SETUP_TOKEN,
            "email": ADMIN_EMAIL,
            "name": ADMIN_NAME,
            "password": ADMIN_PASSWORD,
            "confirm_password": ADMIN_PASSWORD,
        },
    )
    assert resp.status_code in (200, 302), resp.text[:300]
    if resp.status_code == 200:
        assert "already complete" not in resp.text.lower()

    # 4. Login — the first admin must NOT be gated on email verification
    #    (B3: setup-token possession is the ownership proof; no mailer exists).
    resp = await client.get("/admin/login")
    assert resp.status_code == 200
    _assert_page_hygiene(resp.text, context="login form")
    csrf = _csrf_token_from(resp.text)

    resp = await client.post(
        "/admin/login",
        data={
            "csrf_token": csrf,
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        },
    )
    assert resp.status_code == 302, resp.text[:300]
    location = resp.headers["location"]
    assert "verify-email" not in location, (
        f"first admin still gated on email verification: {location}"
    )
    assert "error=" not in location, f"login failed: {location}"

    # 5. Dashboard: 200, sidebar shows the resource (B1/B2), page hygiene.
    resp = await client.get("/admin/")
    assert resp.status_code == 200
    _assert_page_hygiene(resp.text, context="dashboard")
    assert 'href="/admin/gadgets"' in resp.text, "resource missing from sidebar"

    # 6. Resource list: the super admin must not be 403'd (B1).
    resp = await client.get("/admin/gadgets")
    assert resp.status_code == 200, f"super admin denied: {resp.status_code}"
    assert "Seed Gadget" in resp.text

    # 7. Create a record through the real form (CSRF round-trip).
    resp = await client.get("/admin/gadgets/create")
    assert resp.status_code == 200
    csrf = _csrf_token_from(resp.text)

    resp = await client.post(
        "/admin/gadgets/create",
        data={"csrf_token": csrf, "name": "New Gadget", "sku": "SKU-0002"},
    )
    assert resp.status_code in (200, 302, 303), resp.text[:300]

    resp = await client.get("/admin/gadgets")
    assert "New Gadget" in resp.text, "created record not in list"

    # 8. Edit it.
    resp = await client.get("/admin/gadgets/2/edit")
    assert resp.status_code == 200
    csrf = _csrf_token_from(resp.text)

    resp = await client.post(
        "/admin/gadgets/2/edit",
        data={"csrf_token": csrf, "name": "Renamed Gadget", "sku": "SKU-0002"},
    )
    assert resp.status_code in (200, 302, 303), resp.text[:300]

    resp = await client.get("/admin/gadgets")
    assert "Renamed Gadget" in resp.text, "edited record not reflected in list"

    # 9. Logout ends the session; protected pages redirect again.
    resp = await client.get("/admin/logout")
    assert resp.status_code in (302, 303)

    resp = await client.get("/admin/gadgets")
    assert resp.status_code in (302, 307), "session survived logout"
    assert "/login" in resp.headers.get("location", "")


@pytest.mark.asyncio
async def test_second_setup_submission_is_locked_out(
    client: httpx.AsyncClient,
) -> None:
    """After the first admin exists, the wizard refuses further submissions."""
    # Complete setup once.
    resp = await client.get("/admin/setup")
    csrf = _csrf_token_from(resp.text)
    resp = await client.post(
        "/admin/setup",
        data={
            "csrf_token": csrf,
            "setup_token": SETUP_TOKEN,
            "email": ADMIN_EMAIL,
            "name": ADMIN_NAME,
            "password": ADMIN_PASSWORD,
            "confirm_password": ADMIN_PASSWORD,
        },
    )
    assert resp.status_code in (200, 302)

    # A second submission must not create another account.
    resp = await client.get("/admin/setup")
    if resp.status_code == 200 and 'name="csrf_token"' in resp.text:
        csrf = _csrf_token_from(resp.text)
        resp = await client.post(
            "/admin/setup",
            data={
                "csrf_token": csrf,
                "setup_token": SETUP_TOKEN,
                "email": "second@example.test",
                "name": "Second Operator",
                "password": ADMIN_PASSWORD,
                "confirm_password": ADMIN_PASSWORD,
            },
        )
        assert resp.status_code in (200, 302, 403)
        if resp.status_code == 200:
            assert "already complete" in resp.text.lower()

    # Either way: the second identity must not be able to log in.
    resp = await client.get("/admin/login")
    csrf = _csrf_token_from(resp.text)
    resp = await client.post(
        "/admin/login",
        data={
            "csrf_token": csrf,
            "email": "second@example.test",
            "password": ADMIN_PASSWORD,
        },
    )
    # Failed login → redirect back with error, or re-rendered form.
    assert resp.status_code in (200, 302, 401)
    if resp.status_code == 302:
        assert resp.headers["location"].rstrip("/") != "/admin"
