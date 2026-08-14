"""RolesResource.can_update gate, wired into the update HTTP path.

Resource-level: ``can_update`` blocks protected roles (``is_system`` or
the configured super-admin role name) and allows custom roles.
Route-level: ``ResourceController.update()`` consults ``can_update`` —
a protected-record update returns 403 and never reaches the data
source write.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from starlette.requests import Request
from unittest.mock import MagicMock

from lexigram.admin.config import AdminRbacConfig
from lexigram.admin.controllers.resource import ResourceController, ResourceMeta
from lexigram.admin.resources.roles import RolesResource
from lexigram.contracts.auth import RoleDefinition


class TestRolesCanUpdate:
    def _resource(self, role: str = "root") -> RolesResource:
        return RolesResource(rbac_config=AdminRbacConfig(super_admin_role=role))

    def test_blocks_system_role(self) -> None:
        assert (
            self._resource().can_update(RoleDefinition(name="admin", is_system=True))
            is False
        )

    def test_blocks_configured_super_admin_role(self) -> None:
        resource = self._resource("root")
        assert (
            resource.can_update(RoleDefinition(name="root", is_system=False)) is False
        )

    def test_allows_custom_role(self) -> None:
        assert (
            self._resource().can_update(RoleDefinition(name="editor", is_system=False))
            is True
        )

    def test_default_role_name_still_protected(self) -> None:
        resource = RolesResource()
        assert (
            resource.can_update(RoleDefinition(name="superadmin", is_system=False))
            is False
        )


@dataclass
class _FakeItem:
    id: str = "1"
    name: str = "Test Item"


class _FakeDataSource:
    def __init__(self, items: list[_FakeItem] | None = None) -> None:
        self._items = {item.id: item for item in (items or [_FakeItem()])}
        self.update_calls: list[tuple[Any, dict[str, Any]]] = []

    async def find_one(self, item_id: Any) -> _FakeItem | None:
        return self._items.get(str(item_id))

    async def update(self, item_id: Any, data: dict[str, Any]) -> _FakeItem | None:
        self.update_calls.append((item_id, data))
        item = self._items.get(str(item_id))
        if item is None:
            return None
        if "name" in data:
            item.name = data["name"]
        return item


class _GatedController(ResourceController[_FakeItem]):
    meta = ResourceMeta(
        name="role", label="Role", label_plural="Roles", prefix="/admin"
    )

    def __init__(
        self,
        data_source: _FakeDataSource,
        protected: str = "root",
    ) -> None:
        super().__init__(data_source=data_source)
        self._protected = protected

    def get_data_source(self) -> _FakeDataSource:
        assert self._data_source is not None
        return self._data_source

    def can_update(self, item: _FakeItem) -> bool:
        return item.name != self._protected


class TestRolesCanUpdateGateway:
    def setup_method(self) -> None:
        self.ds = _FakeDataSource([_FakeItem(id="1", name="root")])
        self.controller = _GatedController(self.ds)

    def _request(
        self, form_data: dict[str, Any], path_params: dict[str, Any]
    ) -> Request:
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/admin/role/1",
            "query_string": b"",
            "headers": [],
            "path_params": path_params,
            "app": None,
            "state": MagicMock(),
        }
        scope["state"].user = None
        request = Request(scope)

        async def _form() -> dict:
            return dict(form_data)

        request.form = _form  # type: ignore[method-assign]
        return request

    @pytest.mark.asyncio
    async def test_protected_role_update_blocked_with_403(self) -> None:
        request = self._request({"name": "renamed-root"}, path_params={"id": "1"})
        response = await self.controller.update(request)
        assert response.status_code == 403
        assert self.ds.update_calls == []

    @pytest.mark.asyncio
    async def test_ordinary_role_update_succeeds(self) -> None:
        self.ds = _FakeDataSource([_FakeItem(id="1", name="editor")])
        self.controller = _GatedController(self.ds)
        request = self._request({"name": "renamed-editor"}, path_params={"id": "1"})
        response = await self.controller.update(request)
        assert response.status_code == 302
        assert len(self.ds.update_calls) == 1
        assert self.ds._items["1"].name == "renamed-editor"
