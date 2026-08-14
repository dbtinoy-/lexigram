"""Verify resource-resolution failures fail fast in strict mode."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class _FakeDb:
    """Minimal DatabaseProviderProtocol fake — boot resolves the user store
    (DirectSQLAdminUserStore), whose constructor requires a DB provider."""

    def __init__(self) -> None:
        self.database_type = "sqlite"

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def is_connected(self) -> bool:
        return True

    async def get_primary_pool(self) -> object:
        return None

    async def execute_query(
        self, sql: str, params: list[object] | None = None
    ) -> list[dict[str, object]]:
        return []

    async def execute_insert(
        self, sql: str, params: list[object] | None = None
    ) -> list[dict[str, object]]:
        return []

    async def execute_update(
        self, sql: str, params: list[object] | None = None
    ) -> list[dict[str, object]]:
        return []

    async def execute_delete(
        self, sql: str, params: list[object] | None = None
    ) -> list[dict[str, object]]:
        return []

    async def execute(
        self, sql: str, params: list[object] | None = None
    ) -> list[dict[str, object]]:
        return []

    def transaction(self, isolation_level: object = None) -> object:
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _tx() -> object:
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

    async def health_check(self, timeout: float = 5.0) -> object:
        return None

    def scoped_context(self) -> object:
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _ctx() -> object:
            yield None

        return _ctx()

    async def get_scoped_connection(self) -> object:
        return None

    async def release(self, connection: object) -> None:
        return None

    async def acquire(self) -> object:
        return None


class _BrokenResource:
    """Resource class that will raise on resolution."""

    name = "broken"

    def __init__(self) -> None:
        raise RuntimeError("intentional breakage for test")


@pytest.fixture
def mock_app() -> MagicMock:
    app = MagicMock()
    app.state = MagicMock()
    return app


@pytest.mark.asyncio
async def test_strict_mode_raises_on_resource_resolution_failure(
    mock_app: MagicMock,
) -> None:
    """When strict_resource_resolution=True, a failure must propagate."""
    from lexigram.admin.config import AdminConfig
    from lexigram.admin.di.bundle_provider import AdminProvider
    from lexigram.di.container import Container

    config = AdminConfig.from_dict(
        {
            "strict_resource_resolution": True,
            "auth": {"security": {"setup_token": "test-setup-token"}},
        }
    )
    provider = AdminProvider(
        config=config,
        resources=[_BrokenResource],
    )
    container = Container()
    from lexigram.contracts.data import DatabaseProviderProtocol

    container.singleton(DatabaseProviderProtocol, _FakeDb())
    await provider.register(container)
    await provider.boot(container)
    with pytest.raises(RuntimeError, match="intentional breakage"):
        await provider.mount_to_app(mock_app, container)


@pytest.mark.asyncio
async def test_permissive_mode_swallows_resource_resolution_failure(
    mock_app: MagicMock,
) -> None:
    """When strict_resource_resolution=False, a failure must be logged but not raised."""
    from lexigram.admin.config import AdminConfig
    from lexigram.admin.di.bundle_provider import AdminProvider
    from lexigram.di.container import Container

    config = AdminConfig.from_dict(
        {
            "strict_resource_resolution": False,
            "auth": {"security": {"setup_token": "test-setup-token"}},
        }
    )
    provider = AdminProvider(
        config=config,
        resources=[_BrokenResource],
    )
    container = Container()
    from lexigram.contracts.data import DatabaseProviderProtocol

    container.singleton(DatabaseProviderProtocol, _FakeDb())
    await provider.register(container)
    await provider.boot(container)
    # Should not raise
    await provider.mount_to_app(mock_app, container)
