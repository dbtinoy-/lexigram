"""Regression tests for mounted field and detail inline-edit mutations."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel
from starlette.datastructures import FormData
from starlette.requests import Request

from lexigram.admin.config import AdminConfig
from lexigram.admin.resources.action_handlers import InlineMutationActionHandler
from lexigram.admin.resources.base import Resource
from lexigram.admin.schema import TextField


class _InlineModel(BaseModel):
    name: str
    enabled: bool = False
    count: int = 0


class _InlineDataSource:
    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {
            "1": {"id": "1", "name": "Before", "enabled": False, "count": 1}
        }

    async def find_one(self, item_id: Any) -> dict[str, Any] | None:
        return self.records.get(str(item_id))

    async def update(self, item_id: Any, data: dict[str, Any]) -> dict[str, Any] | None:
        record = self.records.get(str(item_id))
        if record is None:
            return None
        record.update(data)
        return record


class _InlineResource(Resource):
    name = "items"
    model = _InlineModel


@pytest.fixture
def resource() -> _InlineResource:
    item = _InlineResource()
    # Keep the fake deliberately small; mounted resources may use any
    # IDataSource-compatible adapter, while this handler only needs the
    # find_one/update mutation surface.
    item._data_source = _InlineDataSource()
    return item


def _request(
    method: str,
    path: str,
    *,
    action: str,
    path_params: dict[str, str],
    form: FormData | None = None,
) -> Request:
    scope: dict[str, Any] = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
        "scheme": "http",
        "root_path": "",
        "path_params": path_params,
        "admin_action": action,
        "admin_prefix": "/admin",
    }
    request = Request(scope)
    if form is not None:
        request.scope["admin_form_data"] = form
    return request


@pytest.mark.asyncio
async def test_field_post_coerces_and_updates_only_requested_field(
    resource: _InlineResource,
) -> None:
    handler = InlineMutationActionHandler(
        AdminConfig(title="Admin", prefix="/admin"),
        "items",
    )
    request = _request(
        "POST",
        "/admin/items/1/field/count",
        action="field",
        path_params={"id": "1", "field": "count"},
        form=FormData([("count", "42")]),
    )

    response = await handler.handle(request, resource)

    assert response.status_code == 200
    assert resource._data_source.records["1"]["count"] == 42  # type: ignore[attr-defined]
    assert resource._data_source.records["1"]["name"] == "Before"  # type: ignore[attr-defined]
    assert 'hx-get="/admin/items/1/field/count"' in response.body.decode()


@pytest.mark.asyncio
async def test_inline_patch_returns_updated_table_row(
    resource: _InlineResource,
) -> None:
    handler = InlineMutationActionHandler(
        AdminConfig(title="Admin", prefix="/admin"),
        "items",
    )
    request = _request(
        "PATCH",
        "/admin/items/1/inline",
        action="inline",
        path_params={"id": "1"},
        form=FormData([("name", "After")]),
    )
    # PATCH submits the field name in the query string.
    request.scope["query_string"] = b"field=name"

    response = await handler.handle(request, resource)

    assert response.status_code == 200
    assert resource._data_source.records["1"]["name"] == "After"  # type: ignore[attr-defined]
    body = response.body.decode()
    assert body.startswith("<tr>")
    assert "After" in body
    assert 'hx-get="/admin/items/1/field/name"' in body


@pytest.mark.asyncio
async def test_inline_mutation_rejects_declared_readonly_fields(
    resource: _InlineResource,
) -> None:
    resource.readonly_fields = ("count",)
    handler = InlineMutationActionHandler(
        AdminConfig(title="Admin", prefix="/admin"),
        "items",
    )
    request = _request(
        "POST",
        "/admin/items/1/field/count",
        action="field",
        path_params={"id": "1", "field": "count"},
        form=FormData([("count", "42")]),
    )

    response = await handler.handle(request, resource)

    assert response.status_code == 403
    assert resource._data_source.records["1"]["count"] == 1  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_inline_mutation_honors_explicit_field_visibility(
    resource: _InlineResource,
) -> None:
    class RestrictedResource(_InlineResource):
        fields = [TextField(name="name", visible_in_form=False)]

    restricted = RestrictedResource()
    restricted._data_source = resource._data_source
    handler = InlineMutationActionHandler(
        AdminConfig(title="Admin", prefix="/admin"),
        "items",
    )
    request = _request(
        "POST",
        "/admin/items/1/field/name",
        action="field",
        path_params={"id": "1", "field": "name"},
        form=FormData([("name", "After")]),
    )

    response = await handler.handle(request, restricted)

    assert response.status_code == 403
    assert resource._data_source.records["1"]["name"] == "Before"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_inline_mutation_rejects_masked_fields(
    resource: _InlineResource,
) -> None:
    class MaskedPermissions:
        async def can_view_field(
            self, user: Any, resource_name: str, field_name: str
        ) -> bool:
            return True

        async def can_edit_field(
            self, user: Any, resource_name: str, field_name: str
        ) -> bool:
            return True

        async def should_mask_field(
            self, user: Any, resource_name: str, field_name: str
        ) -> bool:
            return field_name == "name"

    handler = InlineMutationActionHandler(
        AdminConfig(title="Admin", prefix="/admin"),
        "items",
    )
    request = _request(
        "POST",
        "/admin/items/1/field/name",
        action="field",
        path_params={"id": "1", "field": "name"},
        form=FormData([("name", "After")]),
    )
    request.scope["state"] = {"user": object()}
    request.scope["app"] = SimpleNamespace(
        state=SimpleNamespace(permission_service=MaskedPermissions())
    )

    response = await handler.handle(request, resource)

    assert response.status_code == 403
    assert resource._data_source.records["1"]["name"] == "Before"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_inline_mutation_rejects_unknown_or_readonly_fields(
    resource: _InlineResource,
) -> None:
    handler = InlineMutationActionHandler(
        AdminConfig(title="Admin", prefix="/admin"),
        "items",
    )
    request = _request(
        "POST",
        "/admin/items/1/field/unknown",
        action="field",
        path_params={"id": "1", "field": "unknown"},
        form=FormData([("unknown", "value")]),
    )

    response = await handler.handle(request, resource)

    assert response.status_code == 422
    assert resource._data_source.records["1"]["name"] == "Before"  # type: ignore[attr-defined]
