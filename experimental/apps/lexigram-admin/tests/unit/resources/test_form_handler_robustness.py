"""Regression tests for mounted resource form submission boundaries."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import HTMLResponse

from lexigram.admin.resources.action_handlers import (
    CreateActionHandler,
    EditActionHandler,
)
from lexigram.admin.resources.base import Resource


class _DataSource:
    def __init__(self, record: Any | None = None) -> None:
        self.record = record
        self.created: list[dict[str, Any]] = []
        self.updated: list[tuple[Any, dict[str, Any]]] = []

    async def find_one(self, item_id: Any) -> Any | None:
        return self.record

    async def create(self, data: dict[str, Any]) -> Any:
        self.created.append(data)
        return {"id": "new", **data}

    async def update(self, item_id: Any, data: dict[str, Any]) -> Any:
        self.updated.append((item_id, data))
        return {"id": item_id, **data}


class _Renderer:
    def __init__(self) -> None:
        self.create_call: dict[str, Any] | None = None
        self.edit_call: dict[str, Any] | None = None

    async def render_create(self, request: Request, resource: Any, **kwargs: Any) -> HTMLResponse:
        self.create_call = kwargs
        return HTMLResponse("<form>create</form>")

    async def render_edit(
        self, request: Request, resource: Any, item_id: str, **kwargs: Any
    ) -> HTMLResponse:
        self.edit_call = kwargs
        return HTMLResponse("<form>edit</form>")


def _request(
    method: str,
    data: dict[str, Any],
    *,
    item_id: str = "1",
    user: Any | None = None,
    app: Any | None = None,
) -> Request:
    state: dict[str, Any] = {}
    if user is not None:
        state["user"] = user
    scope: dict[str, Any] = {
        "type": "http",
        "method": method,
        "path": "/backoffice/items/" + (f"{item_id}/edit" if method == "POST" else "create"),
        "raw_path": b"/backoffice/items/create",
        "query_string": b"",
        "headers": [],
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1234),
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "path_params": {"id": item_id},
        "state": state,
        "app": app,
        "session": {},
        # This is populated by AdminCsrfMiddleware after CSRF validation.
        "admin_form_data": data,
        "admin_prefix": "/backoffice",
    }
    return Request(scope)


async def test_create_missing_required_model_field_rerenders_with_422() -> None:
    class Model(BaseModel):
        name: str

    class ItemResource(Resource):
        name = "items"
        model = Model

    source = _DataSource()
    resource = ItemResource()
    resource._data_source = source
    renderer = _Renderer()

    response = await CreateActionHandler(renderer)._handle_create(
        _request("POST", {}), resource
    )

    assert response.status_code == 422
    assert renderer.create_call is not None
    assert renderer.create_call["errors"]["name"]
    assert source.created == []


async def test_create_hook_value_error_rerenders_as_form_level_error() -> None:
    class Model(BaseModel):
        name: str

    class ItemResource(Resource):
        name = "items"
        model = Model

        async def before_create(self, data: dict[str, Any]) -> dict[str, Any]:
            raise ValueError("A record with this name already exists")

    source = _DataSource()
    resource = ItemResource()
    resource._data_source = source
    renderer = _Renderer()

    response = await CreateActionHandler(renderer)._handle_create(
        _request("POST", {"name": "Ada"}), resource
    )

    assert response.status_code == 422
    assert renderer.create_call is not None
    assert renderer.create_call["errors"] == {
        "__all__": ["A record with this name already exists"]
    }
    assert source.created == []


async def test_edit_validates_against_existing_record_without_writing_readonly_data() -> None:
    class Model(BaseModel):
        name: str
        internal_note: str

    class ItemResource(Resource):
        name = "items"
        model = Model
        readonly_fields = ("internal_note",)

    source = _DataSource({"id": "1", "name": "Old", "internal_note": "server"})
    resource = ItemResource()
    resource._data_source = source
    renderer = _Renderer()

    response = await EditActionHandler(renderer)._handle_update(
        _request("POST", {"name": "New"}), resource, "1"
    )

    assert response.status_code == 302
    assert source.updated == [("1", {"name": "New"})]


async def test_submitted_field_without_view_permission_is_rejected() -> None:
    class Model(BaseModel):
        name: str

    class ItemResource(Resource):
        name = "items"
        model = Model

    class PermissionService:
        async def can_view_field(self, user: Any, resource: str, field: str) -> bool:
            return False

        async def can_edit_field(self, user: Any, resource: str, field: str) -> bool:
            return True

    app = SimpleNamespace(state=SimpleNamespace(permission_service=PermissionService()))
    source = _DataSource()
    resource = ItemResource()
    resource._data_source = source

    response = await CreateActionHandler(_Renderer())._handle_create(
        _request("POST", {"name": "Ada"}, user=object(), app=app),
        resource,
    )

    assert response.status_code == 403
    assert source.created == []


async def test_submitted_field_without_edit_permission_is_rejected() -> None:
    class Model(BaseModel):
        name: str
        locked: str

    class ItemResource(Resource):
        name = "items"
        model = Model

    class PermissionService:
        async def can_edit_field(self, user: Any, resource: str, field: str) -> bool:
            return field != "locked"

    app = SimpleNamespace(state=SimpleNamespace(permission_service=PermissionService()))
    source = _DataSource()
    resource = ItemResource()
    resource._data_source = source

    response = await CreateActionHandler(_Renderer())._handle_create(
        _request("POST", {"name": "Ada", "locked": "forged"}, user=object(), app=app),
        resource,
    )

    assert response.status_code == 403
    assert source.created == []
