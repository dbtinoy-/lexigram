"""Live dev playground for the lexigram-admin panel.

Boots the REAL admin lifecycle — ``Container`` → ``DatabaseProvider``
(SQLite) → ``create_app()`` → uvicorn — with two demo resources backed by
in-memory stores, while every auth/session/audit store runs on real SQL.
Default security settings are kept ON so the first-run path behaves exactly
like a fresh production install.

Usage (from the repository root)::

    rm -f experimental/apps/lexigram-admin/playground/playground.db*  # fresh start
    uv run python experimental/apps/lexigram-admin/playground/serve.py

Then open http://localhost:8000/admin/ — the setup wizard appears on a
fresh database. Setup token: ``dev-setup-token``.

Verification workflow: docs/09-01-2026/04-verification-playbook.md.
A clean boot must print ZERO tracebacks (roadmap R8).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from lexigram.admin.actions.standard.header import CreateAction
from lexigram.admin.actions.standard.imports import ImportAction
from lexigram.admin.actions.standard.row import DeleteAction, EditAction
from lexigram.admin.config import AdminConfig
from lexigram.admin.data.data_source import QueryResult
from lexigram.admin.resources import Resource
from lexigram.di.container import Container
from lexigram.sql.di.provider import DatabaseProvider
from lexigram.ui.columns.types import TextColumn

HERE = Path(__file__).parent
DB_PATH = HERE / "playground.db"
SETUP_TOKEN = "dev-setup-token"  # noqa: S105 — local dev playground only
PORT = 8000


# ── In-memory demo store ────────────────────────────────────────────────────


class MemoryStore:
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
        return sum(1 for i in ids if (await self.update(i, data)) is not None)

    async def bulk_delete(self, ids: list[Any]) -> int:
        return sum(1 for i in ids if await self.delete(i))


class ProductStore(MemoryStore):
    pass


class CustomerStore(MemoryStore):
    pass


# ── Demo resources ──────────────────────────────────────────────────────────


class ProductModel(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    sku: str = Field(min_length=1, max_length=40)
    price: float = Field(ge=0)


class ProductResource(Resource):
    name = "products"
    label = "Products"
    icon = "package"
    model = ProductModel
    _data_source_class = ProductStore

    columns = [
        TextColumn("name").sortable(),
        TextColumn("sku").sortable(),
        TextColumn("price").sortable(),
    ]
    search_fields = ["name", "sku"]
    page_size = 10
    default_sort = "name"
    actions = [EditAction(), DeleteAction()]
    header_actions = [
        CreateAction(),
        ImportAction(example_columns=["name", "sku", "price"]),
    ]
    permissions = None


class CustomerModel(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)


class CustomerResource(Resource):
    name = "customers"
    label = "Customers"
    icon = "users"
    model = CustomerModel
    _data_source_class = CustomerStore

    columns = [TextColumn("name").sortable(), TextColumn("email").sortable()]
    search_fields = ["name", "email"]
    page_size = 10
    default_sort = "name"
    actions = [EditAction(), DeleteAction()]
    header_actions = [CreateAction()]
    permissions = None


def _seed_products() -> list[dict[str, Any]]:
    return [
        {"id": i, "name": f"Product {i:02d}", "sku": f"SKU-{i:04d}", "price": 9.5 + i}
        for i in range(1, 21)
    ]


def _seed_customers() -> list[dict[str, Any]]:
    return [
        {"id": i, "name": f"Customer {i:02d}", "email": f"customer{i:02d}@example.dev"}
        for i in range(1, 11)
    ]


# ── Boot ────────────────────────────────────────────────────────────────────


async def build_app():
    """Container → DatabaseProvider → create_app, the real lifecycle."""
    from lexigram.admin.bootstrap import create_app

    container = Container()
    db = DatabaseProvider(config=f"sqlite+aiosqlite:///{DB_PATH}")
    await db.register(container)
    await db.boot(container)

    container.singleton(ProductStore, ProductStore(_seed_products()))
    container.singleton(CustomerStore, CustomerStore(_seed_customers()))

    config = AdminConfig.from_dict(
        {
            "prefix": "/admin",
            "title": "Lexigram Admin Playground",
            # Debug on: exercises the R11 console-mailer fallback so
            # verification/reset emails land in the server log.
            "debug": True,
            "auth": {
                "session_secret": "playground-session-secret-not-for-prod",
                "security": {"setup_token": SETUP_TOKEN},
                # Email verification enforcement stays at its default (ON)
                # and no mailer is configured — the fresh-install path.
            },
        }
    )

    return await create_app(
        resources=[ProductResource, CustomerResource],
        config=config,
        container=container,
    )


def main() -> None:
    import uvicorn

    app = asyncio.run(build_app())
    print(f"\n▶ Admin playground: http://localhost:{PORT}/admin/")
    print(f"▶ Setup token: {SETUP_TOKEN}\n")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")  # noqa: S104 — dev playground binds all interfaces for sandbox preview


if __name__ == "__main__":
    main()
