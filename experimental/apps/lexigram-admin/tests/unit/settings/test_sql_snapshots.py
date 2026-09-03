"""Durable settings history tests against the real SQLite database provider."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from starlette.requests import Request

from lexigram.admin.controllers.settings import SettingsController
from lexigram.admin.services.settings_service import (
    AdminSettingsDbProvider,
    AdminSettingsService,
)
from lexigram.admin.settings.panel.nodes import ConfigSpec, SecretNode, StringNode
from lexigram.admin.settings.panel.registry import ConfigRegistry
from lexigram.admin.settings.snapshots import (
    SettingsSnapshotService,
    SqlSettingsSnapshotStore,
)
from lexigram.admin.settings.store import TenantConfigStore
from lexigram.sql.providers.sqlite_provider import SQLiteProvider


class _SqlHistorySpec(ConfigSpec):
    """Small tenant-scoped spec used for the end-to-end controller checks."""

    namespace = "admin.sql_history_test"
    label = "SQL history test"
    package_source = "tests"
    scope = "tenant"
    title = StringNode(label="Title", default="default title")
    api_key = SecretNode(label="API key", default="")


class _User:
    permissions = frozenset({"admin.settings.edit"})
    roles: list[str] = []
    user_id = "sql-user"
    username = "sql-admin"


@pytest_asyncio.fixture
async def sqlite_provider(tmp_path):
    """Use a file-backed provider so the test also covers reconnect persistence."""
    provider = SQLiteProvider(str(tmp_path / "settings.sqlite3"))
    await provider.connect()
    try:
        yield provider
    finally:
        await provider.disconnect()


def _request(
    *,
    tenant_id: str = "tenant-a",
    headers: dict[str, str] | None = None,
    form: dict[str, Any] | None = None,
) -> MagicMock:
    """Build the narrow request surface used by the settings controller."""
    request = MagicMock(spec=Request)
    request.method = "POST" if form is not None else "GET"
    request.headers = headers or {}
    request.query_params = {}
    request.path_params = {"namespace": _SqlHistorySpec.namespace}
    request.state = SimpleNamespace(user=_User(), tenant_id=tenant_id)
    request.scope = {}
    if form is not None:
        request.scope["admin_form_data"] = form
    return request


async def _build_controller(db: SQLiteProvider) -> SettingsController:
    """Wire the same DB-backed settings and snapshot adapters used in a mount."""
    config_provider = AdminSettingsDbProvider(db)
    settings_service = AdminSettingsService(config_provider)
    registry = ConfigRegistry()
    registry.register_spec(_SqlHistorySpec)
    registry.register_store("db", TenantConfigStore(settings_service))
    return SettingsController(
        renderer=MagicMock(),
        settings_service=settings_service,
        registry=registry,
        snapshot_service=SettingsSnapshotService(SqlSettingsSnapshotStore(db)),
    )


async def _revision(controller: SettingsController, tenant_id: str) -> str:
    values = await controller._registry.get_values(
        _SqlHistorySpec.namespace,
        "db",
        tenant_id=tenant_id,
    )
    return controller._settings_revision(_SqlHistorySpec, values)


@pytest.mark.asyncio
async def test_sql_snapshot_store_round_trips_secrets_and_tenant_scope(
    sqlite_provider,
) -> None:
    """The durable adapter persists safe rows and never crosses tenants."""
    store = SqlSettingsSnapshotStore(sqlite_provider, max_per_namespace=2)
    service = SettingsSnapshotService(store)

    first = await service.capture(
        "admin.sql_history",
        {"title": "first", "api_key": "never-store-this"},
        secret_keys={"api_key"},
        tenant_id="tenant-a",
        actor_id="user-a",
        comment="initial save",
        unset_keys={"title"},
    )
    await service.capture(
        "admin.sql_history",
        {"title": "other tenant"},
        tenant_id="tenant-b",
    )

    history = await service.list_history("admin.sql_history", "tenant-a")
    assert len(history) == 1
    assert history[0].values == {"title": "first"}
    assert history[0].skipped_secrets == ("api_key",)
    assert history[0].unset_keys == ("title",)
    assert history[0].actor_id == "user-a"
    assert (
        await service.rollback_values(
            first.snapshot_id,
            namespace="admin.sql_history",
            tenant_id="tenant-b",
        )
        is None
    )

    rows = await sqlite_provider.execute_query(
        "SELECT values_json, skipped_secrets FROM admin_settings_snapshots"
    )
    assert "never-store-this" not in str(rows.rows)


@pytest.mark.asyncio
async def test_sql_snapshot_retention_and_reconnect_persistence(
    sqlite_provider, tmp_path
) -> None:
    """Retention is enforced in SQL and retained history survives reconnect."""
    store = SqlSettingsSnapshotStore(sqlite_provider, max_per_namespace=2)
    service = SettingsSnapshotService(store)
    snapshots = [
        await service.capture("admin.sql_history", {"index": index})
        for index in range(3)
    ]

    history = await service.list_history("admin.sql_history", None)
    assert [item.values["index"] for item in history] == [2, 1]
    assert await service.get(snapshots[0].snapshot_id) is None

    await sqlite_provider.disconnect()
    reopened = SQLiteProvider(str(tmp_path / "settings.sqlite3"))
    await reopened.connect()
    try:
        persisted = await SettingsSnapshotService(
            SqlSettingsSnapshotStore(reopened)
        ).list_history("admin.sql_history")
        assert [item.values["index"] for item in persisted] == [2, 1]
    finally:
        await reopened.disconnect()


@pytest.mark.asyncio
async def test_controller_save_and_history_use_sql_adapters(sqlite_provider) -> None:
    """A controller save is visible in the durable history endpoint."""
    controller = await _build_controller(sqlite_provider)
    revision = await _revision(controller, "tenant-a")

    response = await controller.save_spec(
        _request(
            tenant_id="tenant-a",
            form={
                "title": "stored title",
                "api_key": "secret",
                "settings_revision": revision,
            },
        )
    )
    assert response.status_code == 302

    view_response = await controller.spec_view(
        _request(
            tenant_id="tenant-a",
            headers={"hx-request": "true", "hx-target": "#settings-content"},
        )
    )
    assert (
        "/admin/settings/history/admin.sql_history_test" in view_response.body.decode()
    )

    history_response = await controller.history(
        _request(
            tenant_id="tenant-a",
            headers={"hx-request": "true"},
        )
    )
    body = history_response.body.decode()
    assert history_response.status_code == 200
    assert "Change history" in body
    assert "default title" in body
    assert "api_key: secret" not in body

    other_tenant_response = await controller.history(
        _request(
            tenant_id="tenant-b",
            headers={"hx-request": "true"},
        )
    )
    assert "No changes have been recorded" in other_tenant_response.body.decode()


@pytest.mark.asyncio
async def test_sql_controller_rollback_restores_through_normal_save(
    sqlite_provider,
) -> None:
    """Rollback resolves SQL history but still writes through the DB store."""
    controller = await _build_controller(sqlite_provider)
    tenant_id = "tenant-a"

    await controller.save_spec(
        _request(
            tenant_id=tenant_id,
            form={
                "title": "changed",
                "settings_revision": await _revision(controller, tenant_id),
            },
        )
    )
    snapshots = await controller._snapshots.list_history(
        _SqlHistorySpec.namespace, tenant_id
    )
    assert len(snapshots) == 1

    response = await controller.save_spec(
        _request(
            tenant_id=tenant_id,
            form={
                "rollback_to": snapshots[0].snapshot_id,
                "settings_revision": await _revision(controller, tenant_id),
            },
        )
    )
    assert response.status_code == 302

    values = await controller._registry.get_values(
        _SqlHistorySpec.namespace,
        "db",
        tenant_id=tenant_id,
    )
    assert values["title"] == "default title"
    persisted = await sqlite_provider.execute_query(
        "SELECT key FROM tenant_configs WHERE tenant_id = ? AND key = ?",
        [tenant_id, f"admin_ui.{_SqlHistorySpec.namespace}.title"],
    )
    assert persisted.rows == []
    history = await controller._snapshots.list_history(
        _SqlHistorySpec.namespace, tenant_id
    )
    assert len(history) == 2
    assert history[0].unset_keys == ()
