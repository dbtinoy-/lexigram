"""PermissionService: async delegation to the union authorizer (spec §2.2)."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.rbac.schema import FieldPermission, ResourcePermissions
from lexigram.admin.rbac.service import PermissionService


class _FakeAuthorizer:
    """Minimal AuthorizerProtocol fake with configurable decisions."""

    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed

    async def check_access(
        self,
        user: Any,
        allowed_roles: set[str],
        resource: str | None = None,
        action: str | None = None,
    ) -> bool:
        return self.allowed

    async def can(self, user: Any, action: str, resource: str) -> bool:
        return self.allowed

    async def authorize(
        self,
        user: Any,
        action: str,
        resource: str,
    ) -> bool:
        return self.allowed

    async def can_view(
        self, user: Any, resource: str, record: Any = None
    ) -> bool:
        return self.allowed

    async def can_create(self, user: Any, resource: str) -> bool:
        return self.allowed

    async def can_update(
        self, user: Any, resource: str, record: Any = None
    ) -> bool:
        return self.allowed

    async def can_delete(
        self, user: Any, resource: str, record: Any = None
    ) -> bool:
        return self.allowed

    async def can_execute_action(
        self, user: Any, resource: str, action: str, record: Any = None
    ) -> bool:
        return self.allowed

    def set_roles(self, roles: dict[str, Any]) -> None:
        return None

    def register_role(self, name: str, role: Any) -> None:
        return None

    def remove_role(self, name: str) -> None:
        return None

    async def sync_from_db(self, container: Any) -> None:
        return None


@pytest.mark.asyncio
async def test_can_list_is_async_and_denies_when_no_schema_roles() -> None:
    service = PermissionService(authorization_service=_FakeAuthorizer(allowed=False))
    service.register("notes", ResourcePermissions(can_list={"admin"}))
    result = await service.can_list({"user_id": "u1"}, "notes")
    assert result is False


@pytest.mark.asyncio
async def test_can_view_without_authorizer_denies() -> None:
    service = PermissionService()
    service.register("notes", ResourcePermissions(can_view={"admin"}))
    result = await service.can_view({"user_id": "u1"}, "notes")
    assert result is False


@pytest.mark.asyncio
async def test_field_checks_are_async_and_deny_by_default() -> None:
    service = PermissionService(authorization_service=_FakeAuthorizer(allowed=False))
    service.register(
        "notes",
        ResourcePermissions(
            fields={
                "name": FieldPermission(view_roles={"admin"}, edit_roles={"admin"}),
                "secret": FieldPermission(mask_for={"admin"}),
            }
        ),
    )
    assert await service.can_view_field({"user_id": "u1"}, "notes", "name") is False
    assert await service.can_edit_field({"user_id": "u1"}, "notes", "name") is False
    assert await service.should_mask_field({"user_id": "u1"}, "notes", "secret") is False