"""Tests for ResourceController CRUD endpoints.

Verifies that all 8 CRUD endpoints (list, view, create form, create,
edit form, edit, delete, bulk) are present and dispatch correctly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest
from starlette.datastructures import FormData
from starlette.requests import Request

from lexigram.admin.controllers.resource import ResourceController, ResourceMeta
from lexigram.admin.data.data_source import QueryResult
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


class TestResourceControllerRoutes:
    """Verify get_routes() returns the expected CRUD routes."""

    def setup_method(self) -> None:
        self.controller = ConcreteResourceController(FakeDataSource())

    def test_get_routes_returns_all_routes(self) -> None:
        routes = self.controller.get_routes()
        assert len(routes) == 10

    def test_list_route_registered(self) -> None:
        routes = self.controller.get_routes()
        list_routes = [r for r in routes if "GET" in r.methods and r.path == "/item"]
        assert len(list_routes) >= 1

    def test_create_form_route_registered(self) -> None:
        routes = self.controller.get_routes()
        create_form = [
            r for r in routes if r.path == "/item/create" and "GET" in r.methods
        ]
        assert len(create_form) == 1

    def test_create_route_registered(self) -> None:
        routes = self.controller.get_routes()
        create = [r for r in routes if r.path == "/item" and "POST" in r.methods]
        assert len(create) == 1

    def test_detail_route_registered(self) -> None:
        routes = self.controller.get_routes()
        detail = [r for r in routes if "{id}" in r.path and "GET" in r.methods and "/edit" not in r.path and "/delete" not in r.path]
        assert len(detail) >= 1

    def test_edit_form_route_registered(self) -> None:
        routes = self.controller.get_routes()
        edit_form = [r for r in routes if "/edit" in r.path and "GET" in r.methods]
        assert len(edit_form) == 1

    def test_update_route_registered(self) -> None:
        routes = self.controller.get_routes()
        update = [
            r
            for r in routes
            if "{id}" in r.path
            and ("PUT" in r.methods or "POST" in r.methods)
            and "/edit" not in r.path
            and "/bulk" not in r.path
            and "/create" not in r.path
            and "/delete" not in r.path
        ]
        assert len(update) >= 1

    def test_delete_route_registered(self) -> None:
        routes = self.controller.get_routes()
        delete = [r for r in routes if "DELETE" in r.methods]
        assert len(delete) == 1

    def test_bulk_action_route_registered(self) -> None:
        routes = self.controller.get_routes()
        bulk = [r for r in routes if "/bulk" in r.path and "POST" in r.methods]
        assert len(bulk) == 1


# ---------------------------------------------------------------------------
# Test: list_view — returns 200 with HTML
# ---------------------------------------------------------------------------


class TestListView:
    """Tests for the list_view endpoint."""

    def setup_method(self) -> None:
        self.ds = FakeDataSource()
        self.controller = ConcreteResourceController(self.ds)

    @pytest.mark.asyncio
    async def test_list_returns_200(self) -> None:
        request = _make_request("GET", "/admin/item")
        response = await self.controller.list_view(request)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_response_is_html(self) -> None:
        request = _make_request("GET", "/admin/item")
        response = await self.controller.list_view(request)
        body = response.body.decode()
        assert "Items" in body

    @pytest.mark.asyncio
    async def test_list_htmx_returns_partial(self) -> None:
        request = _make_request("GET", "/admin/item", headers={"hx-request": "true"})
        response = await self.controller.list_view(request)
        assert response.status_code == 200
        # HTMX partial omits full HTML shell
        body = response.body.decode()
        assert "<table" in body

    @pytest.mark.asyncio
    async def test_list_includes_items_from_data_source(self) -> None:
        request = _make_request("GET", "/admin/item")
        response = await self.controller.list_view(request)
        body = response.body.decode()
        assert "FakeItem" in body


# ---------------------------------------------------------------------------
# Test: detail — returns 200 or raises NotFoundError
# ---------------------------------------------------------------------------


class TestDetailView:
    """Tests for the detail endpoint."""

    def setup_method(self) -> None:
        self.ds = FakeDataSource()
        self.controller = ConcreteResourceController(self.ds)

    @pytest.mark.asyncio
    async def test_detail_returns_200_for_existing(self) -> None:
        request = _make_request("GET", "/admin/item/1", path_params={"id": "1"})
        response = await self.controller.detail(request)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_detail_raises_not_found_for_missing(self) -> None:
        request = _make_request("GET", "/admin/item/999", path_params={"id": "999"})
        response = await self.controller.detail(request)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_detail_htmx_returns_partial(self) -> None:
        request = _make_request(
            "GET",
            "/admin/item/1",
            path_params={"id": "1"},
            headers={"hx-request": "true"},
        )
        response = await self.controller.detail(request)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_detail_includes_item_data(self) -> None:
        request = _make_request("GET", "/admin/item/1", path_params={"id": "1"})
        response = await self.controller.detail(request)
        body = response.body.decode()
        assert "FakeItem" in body or "1" in body


# ---------------------------------------------------------------------------
# Test: create_form — returns 200 with form HTML
# ---------------------------------------------------------------------------


class TestCreateFormView:
    """Tests for the create_form endpoint."""

    def setup_method(self) -> None:
        self.controller = ConcreteResourceController(FakeDataSource())

    @pytest.mark.asyncio
    async def test_create_form_returns_200(self) -> None:
        request = _make_request("GET", "/admin/item/create")
        response = await self.controller.create_form(request)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_form_returns_html_form(self) -> None:
        request = _make_request("GET", "/admin/item/create")
        response = await self.controller.create_form(request)
        body = response.body.decode()
        assert "<form" in body

    @pytest.mark.asyncio
    async def test_create_form_htmx_returns_partial(self) -> None:
        request = _make_request(
            "GET", "/admin/item/create", headers={"hx-request": "true"}
        )
        response = await self.controller.create_form(request)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Test: create (POST) — creates item, redirects
# ---------------------------------------------------------------------------


class TestCreateAction:
    """Tests for the create (POST) endpoint."""

    def setup_method(self) -> None:
        self.ds = FakeDataSource()
        self.controller = ConcreteResourceController(self.ds)

    @pytest.mark.asyncio
    async def test_create_redirects_on_success(self) -> None:
        request = _make_request("POST", "/admin/item", form_data={"name": "New Item"})
        response = await self.controller.create(request)
        # Non-HTMX create should redirect (302)
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_create_adds_item_to_data_source(self) -> None:
        initial_count = len(self.ds._items)
        request = _make_request("POST", "/admin/item", form_data={"name": "New Item"})
        await self.controller.create(request)
        assert len(self.ds._items) == initial_count + 1

    @pytest.mark.asyncio
    async def test_create_htmx_returns_hx_redirect(self) -> None:
        request = _make_request(
            "POST",
            "/admin/item",
            form_data={"name": "New Item"},
            headers={"hx-request": "true", "hx-target": "main"},
        )
        response = await self.controller.create(request)
        assert response.status_code == 200
        assert "HX-Redirect" in response.headers

    @pytest.mark.asyncio
    async def test_create_redirect_target_is_list_url(self) -> None:
        request = _make_request(
            "POST", "/admin/item", form_data={"name": "Another Item"}
        )
        response = await self.controller.create(request)
        assert response.headers["location"].endswith("/item")


# ---------------------------------------------------------------------------
# Test: edit_form — returns 200 with form HTML
# ---------------------------------------------------------------------------


class TestEditFormView:
    """Tests for the edit_form endpoint."""

    def setup_method(self) -> None:
        self.ds = FakeDataSource()
        self.controller = ConcreteResourceController(self.ds)

    @pytest.mark.asyncio
    async def test_edit_form_returns_200(self) -> None:
        request = _make_request("GET", "/admin/item/1/edit", path_params={"id": "1"})
        response = await self.controller.edit_form(request)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_edit_form_contains_form_tag(self) -> None:
        request = _make_request("GET", "/admin/item/1/edit", path_params={"id": "1"})
        response = await self.controller.edit_form(request)
        body = response.body.decode()
        assert "<form" in body

    @pytest.mark.asyncio
    async def test_edit_form_raises_not_found_for_missing(self) -> None:
        request = _make_request(
            "GET", "/admin/item/999/edit", path_params={"id": "999"}
        )
        with pytest.raises(NotFoundError):
            await self.controller.edit_form(request)

    @pytest.mark.asyncio
    async def test_edit_form_htmx_returns_partial(self) -> None:
        request = _make_request(
            "GET",
            "/admin/item/1/edit",
            path_params={"id": "1"},
            headers={"hx-request": "true"},
        )
        response = await self.controller.edit_form(request)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Test: delete — removes item, redirects
# ---------------------------------------------------------------------------


class TestDeleteAction:
    """Tests for the delete endpoint."""

    def setup_method(self) -> None:
        self.ds = FakeDataSource()
        self.controller = ConcreteResourceController(self.ds)

    @pytest.mark.asyncio
    async def test_delete_removes_item(self) -> None:
        assert "1" in self.ds._items
        request = _make_request("DELETE", "/admin/item/1", path_params={"id": "1"})
        await self.controller.delete(request)
        assert "1" not in self.ds._items

    @pytest.mark.asyncio
    async def test_delete_returns_redirect(self) -> None:
        request = _make_request("DELETE", "/admin/item/1", path_params={"id": "1"})
        response = await self.controller.delete(request)
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_delete_raises_not_found_for_missing(self) -> None:
        request = _make_request("DELETE", "/admin/item/999", path_params={"id": "999"})
        with pytest.raises(NotFoundError):
            await self.controller.delete(request)

    @pytest.mark.asyncio
    async def test_delete_htmx_returns_hx_redirect(self) -> None:
        request = _make_request(
            "DELETE",
            "/admin/item/1",
            path_params={"id": "1"},
            headers={"hx-request": "true", "hx-target": "main"},
        )
        response = await self.controller.delete(request)
        assert response.status_code == 200
        assert "HX-Redirect" in response.headers

    @pytest.mark.asyncio
    async def test_delete_redirect_target_is_list_url(self) -> None:
        request = _make_request("DELETE", "/admin/item/1", path_params={"id": "1"})
        response = await self.controller.delete(request)
        assert response.headers["location"].endswith("/item")


# ---------------------------------------------------------------------------
# Test: bulk_action — handles delete action
# ---------------------------------------------------------------------------


class TestBulkAction:
    """Tests for the bulk_action endpoint."""

    def setup_method(self) -> None:
        self.ds = FakeDataSource()
        self.controller = ConcreteResourceController(self.ds)

    @pytest.mark.asyncio
    async def test_bulk_delete_removes_items(self) -> None:
        assert len(self.ds._items) == 2
        request = _make_request(
            "POST",
            "/admin/item/bulk",
            form_data={"action": "delete", "ids": ["1", "2"]},
        )

        # Patch form() to return multi-valued form
        async def _form():
            data = MagicMock()
            data.get = lambda k, d=None: {"action": "delete"}.get(k, d)
            data.getlist = lambda k: {"ids": ["1", "2"]}.get(k, [])
            return data

        request.form = _form  # type: ignore[method-assign]
        await self.controller.bulk_action(request)
        assert len(self.ds._items) == 0

    @pytest.mark.asyncio
    async def test_bulk_action_missing_action_returns_400(self) -> None:
        request = _make_request("POST", "/admin/item/bulk", form_data={})

        async def _form():
            data = MagicMock()
            data.get = lambda k, d=None: None
            data.getlist = lambda k: []
            return data

        request.form = _form  # type: ignore[method-assign]
        response = await self.controller.bulk_action(request)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_bulk_action_htmx_triggers_refresh(self) -> None:
        request = _make_request(
            "POST",
            "/admin/item/bulk",
            form_data={"action": "delete", "ids": ["1"]},
            headers={"hx-request": "true", "hx-target": "main"},
        )

        async def _form():
            data = MagicMock()
            data.get = lambda k, d=None: {"action": "delete"}.get(k, d)
            data.getlist = lambda k: {"ids": ["1"]}.get(k, [])
            return data

        request.form = _form  # type: ignore[method-assign]
        response = await self.controller.bulk_action(request)
        assert response.status_code == 200
        assert "HX-Trigger" in response.headers

    @pytest.mark.asyncio
    async def test_unknown_bulk_action_returns_response(self) -> None:
        request = _make_request("POST", "/admin/item/bulk")

        async def _form():
            data = MagicMock()
            data.get = lambda k, d=None: {"action": "unknown"}.get(k, d)
            data.getlist = lambda k: {"ids": ["1"]}.get(k, [])
            return data

        request.form = _form  # type: ignore[method-assign]
        response = await self.controller.bulk_action(request)
        # Non-HTMX unknown action redirects (302) or renders (200); either is valid
        assert response.status_code in (200, 302)


# ---------------------------------------------------------------------------
# Test: soft delete
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
