"""One bound authorizer instance across all admin RBAC consumers (spec §2.2)."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.di.bundle_provider import AdminProvider
from lexigram.admin.rbac.protocols import (
    AdminRoleStoreProtocol,
)
from lexigram.admin.rbac.role_service import AdminRoleService
from lexigram.admin.rbac.service import PermissionService
from lexigram.admin.services.action_executor import ActionExecutor
from lexigram.admin.services.action_registry import ActionRegistry
from lexigram.admin.services.resource_manager import ResourceManager
from lexigram.contracts.auth import AuthorizerProtocol
from lexigram.di.container import Container


class _FakeRoleStore:
    """Minimal AdminRoleStoreProtocol fake for container wiring tests."""

    async def ensure_schema(self) -> None:
        return None

    async def list_roles(self) -> list[Any]:
        return []

    async def get_role(self, name: str) -> Any | None:
        return None

    async def create_role(self, role: Any) -> None:
        return None

    async def update_role(self, role: Any) -> None:
        return None

    async def delete_role(self, name: str) -> bool:
        return True


class _FakeDataSource:
    """Minimal ResourceDataSourceProtocol fake for construction tests."""


@pytest.mark.asyncio
async def test_all_consumers_share_one_authorizer_instance() -> None:
    from lexigram.admin.config import AdminConfig

    container = Container()
    provider = AdminProvider(
        config=AdminConfig.from_dict(
            {"auth": {"security": {"setup_token": "test-setup-token"}}}
        )
    )
    await provider.register(container)
    await provider.boot(container)

    container.singleton(AdminRoleStoreProtocol, _FakeRoleStore)

    bound = await container.resolve(AuthorizerProtocol)
    assert await container.resolve(AuthorizerProtocol) is bound

    perms = await container.resolve(PermissionService)
    assert perms.authorization_service is bound

    roles = await container.resolve(AdminRoleService)
    assert roles._authorization_service is bound

    rm = ResourceManager("notes", _FakeDataSource(), authorizer=bound)
    ex = ActionExecutor(ActionRegistry(), authorizer=bound)
    assert rm.authorizer is bound
    assert ex.authorizer is bound
