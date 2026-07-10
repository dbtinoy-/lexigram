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


class _FakeDb:
    """Minimal DatabaseProviderProtocol fake — boot resolves the user store
    via DirectSQLAdminUserStore, whose constructor requires a DB provider."""

    def __init__(self) -> None:
        self.database_type = "sqlite"

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def is_connected(self) -> bool:
        return True

    async def get_primary_pool(self) -> Any:
        return None

    async def execute_query(self, sql: str, params: list[Any] | None = None) -> Any:
        return []

    async def execute_insert(self, sql: str, params: list[Any] | None = None) -> Any:
        return []

    async def execute_update(self, sql: str, params: list[Any] | None = None) -> Any:
        return []

    async def execute_delete(self, sql: str, params: list[Any] | None = None) -> Any:
        return []

    async def execute(self, sql: str, params: list[Any] | None = None) -> Any:
        return []

    def transaction(self, isolation_level: Any = None) -> Any:
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _tx() -> Any:
            yield None

        return _tx()

    async def begin_transaction(self) -> None:
        return None

    async def commit_transaction(self) -> None:
        return None

    async def rollback_transaction(self) -> None:
        return None

    async def table_exists(self, table_name: str) -> bool:
        return True

    async def health_check(self, timeout: float = 5.0) -> Any:
        return None

    def scoped_context(self) -> Any:
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _ctx() -> Any:
            yield None

        return _ctx()

    async def get_scoped_connection(self) -> Any:
        return None

    async def release(self, connection: Any) -> None:
        return None

    async def acquire(self) -> Any:
        return None


@pytest.mark.asyncio
async def test_all_consumers_share_one_authorizer_instance() -> None:
    from lexigram.admin.config import AdminConfig
    from lexigram.contracts.data import DatabaseProviderProtocol

    container = Container()
    container.singleton(DatabaseProviderProtocol, _FakeDb)
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
