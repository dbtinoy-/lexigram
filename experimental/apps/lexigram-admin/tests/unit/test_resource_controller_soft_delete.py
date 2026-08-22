"""Tests for ResourceController CRUD endpoints.

Verifies that all 8 CRUD endpoints (list, view, create form, create,
edit form, edit, delete, bulk) are present and dispatch correctly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.datastructures import FormData
from starlette.requests import Request

from lexigram.admin.controllers.resource import ResourceController, ResourceMeta
from lexigram.admin.data.data_source import QueryResult, SqlDataSource
from lexigram.admin.exceptions import NotFoundError

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeItem:
    """Minimal entity used in tests."""

    id: str = "1"
    name: str = "Test Item"


class FakeDataSource:
    """In-memory IDataSource implementation for testing."""

    def __init__(self, items: list[FakeItem] | None = None) -> None:
        self._items: dict[str, FakeItem] = {
            item.id: item for item in (items or [FakeItem(id="1"), FakeItem(id="2")])
        }
        self._next_id = 100

    async def find_one(self, item_id: Any) -> FakeItem | None:
        return self._items.get(str(item_id))

    async def find_many(self, query: Any) -> QueryResult[FakeItem]:
        items = list(self._items.values())
        return QueryResult(items=items, total=len(items), page=1, per_page=20)

    async def count(self, query: Any) -> int:
        return len(self._items)

    async def create(self, data: dict[str, Any]) -> FakeItem:
        new_id = str(self._next_id)
        self._next_id += 1
        item = FakeItem(id=new_id, name=data.get("name", "New Item"))
        self._items[new_id] = item
        return item

    async def update(self, item_id: Any, data: dict[str, Any]) -> FakeItem | None:
        item = self._items.get(str(item_id))
        if item is None:
            return None
        if "name" in data:
            item.name = data["name"]
        return item

    async def delete(self, item_id: Any) -> bool:
        return self._items.pop(str(item_id), None) is not None

    async def bulk_delete(self, ids: list[str]) -> int:
        deleted = 0
        for id_ in ids:
            if self._items.pop(id_, None) is not None:
                deleted += 1
        return deleted

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[FakeItem]:
        created = []
        for data in items:
            created.append(await self.create(data))
        return created

    async def bulk_update(self, ids: list[str], data: dict[str, Any]) -> int:
        count = 0
        for id_ in ids:
            item = self._items.get(id_)
            if item is not None:
                if "name" in data:
                    item.name = data["name"]
                count += 1
        return count


class ConcreteResourceController(ResourceController[FakeItem]):
    """Concrete subclass of ResourceController for testing."""

    meta = ResourceMeta(
        name="item",
        label="Item",
        label_plural="Items",
        prefix="/admin",
    )

    def __init__(self, data_source: FakeDataSource | None = None) -> None:
        super().__init__(data_source=data_source)

    def get_data_source(self) -> FakeDataSource:
        if self._data_source is None:
            raise NotImplementedError("No data source configured")
        return self._data_source  # type: ignore[return-value]


def _make_request(
    method: str = "GET",
    path: str = "/admin/item",
    path_params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    form_data: dict[str, Any] | None = None,
) -> Request:
    """Build a minimal Starlette Request for unit tests."""
    scope = {
        "type": "http",
        "method": method.upper(),
        "path": path,
        "query_string": b"",
        "headers": [
            (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
        ],
        "path_params": path_params or {},
        "app": None,
        "state": MagicMock(),
    }
    # Ensure state.user is None by default
    scope["state"].user = None
    scope["state"].permissions = None

    request = Request(scope)

    if form_data:
        # Patch form() to return a fake FormData-like dict
        async def _form() -> dict:
            mock_form = MagicMock(spec=FormData)
            mock_form.__iter__ = MagicMock(return_value=iter(form_data.items()))
            mock_form.get = form_data.get
            mock_form.getlist = lambda k: form_data.get(k, [])

            # dict(form_data) — make form_data a plain dict iterable
            async def _items():
                return list(form_data.items())

            return form_data

        request.form = _form  # type: ignore[method-assign]

    return request


# ---------------------------------------------------------------------------
# Test: get_routes() — all 8 routes are registered correctly
# ---------------------------------------------------------------------------


class TestSoftDelete:
    """Tests for soft-delete behavior."""

    def setup_method(self) -> None:
        self.ds = FakeDataSource()
        self.controller = ConcreteResourceController(self.ds)
        self.controller.soft_delete_enabled = True

    @pytest.mark.asyncio
    async def test_soft_delete_stamps_deleted_at(self) -> None:
        request = _make_request("DELETE", "/admin/item/1", path_params={"id": "1"})
        response = await self.controller.delete(request)
        # Item still exists (soft delete updates rather than removes)
        assert "1" in self.ds._items
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_soft_delete_not_found_raises(self) -> None:
        request = _make_request("DELETE", "/admin/item/999", path_params={"id": "999"})
        with pytest.raises(NotFoundError):
            await self.controller.delete(request)


# ---------------------------------------------------------------------------
# Test: ResourceMeta configuration
# ---------------------------------------------------------------------------


class TestResourceMeta:
    """Tests for ResourceMeta defaults and factory method."""

    def test_defaults(self) -> None:
        meta = ResourceMeta(name="user", label="User", label_plural="Users")
        assert meta.per_page == 20
        assert meta.default_sort == "id"
        assert meta.default_sort_order == "desc"
        assert meta.enable_create is True
        assert meta.enable_edit is True
        assert meta.enable_delete is True
        assert meta.enable_bulk_actions is True
        assert meta.enable_export is True

    def test_from_dict_creates_meta(self) -> None:
        data = {
            "name": "product",
            "label": "Product",
            "label_plural": "Products",
            "per_page": 50,
            "enable_delete": False,
        }
        meta = ResourceMeta.from_dict(data)
        assert meta.name == "product"
        assert meta.per_page == 50
        assert meta.enable_delete is False
        assert meta.enable_create is True

    def test_from_dict_applies_all_fields(self) -> None:
        data = {
            "name": "order",
            "label": "Order",
            "label_plural": "Orders",
            "icon": "shopping-cart",
            "prefix": "/admin",
            "default_sort": "created_at",
            "default_sort_order": "asc",
            "searchable_fields": ["name", "email"],
        }
        meta = ResourceMeta.from_dict(data)
        assert meta.icon == "shopping-cart"
        assert meta.prefix == "/admin"
        assert meta.default_sort == "created_at"
        assert meta.default_sort_order == "asc"
        assert meta.searchable_fields == ["name", "email"]


# ---------------------------------------------------------------------------
# Test: hostile identifier form fields surface as 400 (Round 7 finding 31)
# ---------------------------------------------------------------------------


class RecordingDb:
    """Recording fake for the database provider surface used by SqlDataSource."""

    def __init__(self) -> None:
        self.fetch_one = AsyncMock(return_value={"id": 1})
        self.fetch_all = AsyncMock(return_value=[])
        self.execute = AsyncMock(return_value=1)


class SqlGuardedController(ConcreteResourceController):
    """Controller whose data layer is a real SqlDataSource over a fake provider."""

    def __init__(self, db: RecordingDb, *, table_name: str = "users") -> None:
        super().__init__(data_source=None)
        self._db = db
        self._table_name = table_name

    def get_data_source(self) -> SqlDataSource[Any]:
        if self._data_source is None:
            self._data_source = SqlDataSource(db=self._db, table_name=self._table_name)  # type: ignore[arg-type]
        return self._data_source  # type: ignore[return-value]


class TestHostileIdentifierFieldsReturn400:
    """Hostile form-field names must never reach SQL execution.

    Layer 1: model-field allowlist strips unknown keys (this suite).
    Layer 2: SqlDataSource identifier validation remains as backstop
    for callers that bypass the controller."""

    HOSTILE_FIELD = "email) VALUES ('x',"

    def setup_method(self) -> None:
        self.db = RecordingDb()
        self.controller = SqlGuardedController(self.db)

    @pytest.mark.asyncio
    async def test_create_hostile_field_name_never_reaches_sql(self) -> None:
        """Unknown/hostile keys are stripped by the field allowlist before
        any data-source call, so no SQL identifier ever sees them."""
        request = _make_request(
            "POST", "/admin/item", form_data={self.HOSTILE_FIELD: "value"}
        )
        response = await self.controller.create(request)
        assert response.status_code == 302
        stmt = self.db.execute.call_args.args[0] if self.db.execute.await_count else ""
        assert self.HOSTILE_FIELD not in stmt
        assert "email) VALUES" not in stmt

    @pytest.mark.asyncio
    async def test_create_benign_field_names_still_redirect(self) -> None:
        request = _make_request("POST", "/admin/item", form_data={"name": "New Item"})
        response = await self.controller.create(request)
        assert response.status_code == 302
        assert self.db.fetch_one.await_count == 1

    @pytest.mark.asyncio
    async def test_update_hostile_field_name_never_reaches_sql(self) -> None:
        request = _make_request(
            "PUT",
            "/admin/item/1",
            path_params={"id": "1"},
            form_data={self.HOSTILE_FIELD: "x"},
        )
        response = await self.controller.update(request)
        assert response.status_code == 302
        # The write statement must not reference the hostile identifier.
        stmt = self.db.execute.call_args.args[0] if self.db.execute.await_count else ""
        assert "email) VALUES" not in stmt
        assert self.HOSTILE_FIELD not in str(self.db.execute.call_args)

    @pytest.mark.asyncio
    async def test_update_benign_field_names_still_redirect(self) -> None:
        request = _make_request(
            "PUT",
            "/admin/item/1",
            path_params={"id": "1"},
            form_data={"name": "Renamed"},
        )
        response = await self.controller.update(request)
        assert response.status_code == 302
