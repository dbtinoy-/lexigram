"""Tests for SQLTenantProvider."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from lexigram.contracts.tenancy.commands import CreateTenantCommand, UpdateTenantCommand
from lexigram.contracts.tenancy.errors import TenantNotFoundError
from lexigram.contracts.tenancy.types import TenantInfo, TenantStatus
from lexigram.tenancy.stores.sql import SQLTenantProvider


@pytest.fixture
def mock_db() -> MagicMock:
    """Create a mock DatabaseProviderProtocol."""
    db = MagicMock()
    ctx = AsyncMock()
    ctx.fetch_one = AsyncMock(return_value=None)
    ctx.fetch_all = AsyncMock(return_value=[])
    ctx.execute = AsyncMock(return_value=None)
    ctx.__aenter__ = AsyncMock(return_value=ctx)
    ctx.__aexit__ = AsyncMock(return_value=None)
    db.scoped_context = MagicMock(return_value=ctx)
    return db


@pytest.fixture
def provider(mock_db: MagicMock) -> SQLTenantProvider:
    """Create SQLTenantProvider with mock DB."""
    return SQLTenantProvider(db=mock_db)


def _make_row(
    tenant_id: str = "tenant-abc",
    slug: str = "acme",
    name: str = "ACME Corp",
    status: str = "active",
    plan: str | None = None,
    config: str = "{}",
    metadata: str = "{}",
    created_at: datetime | None = None,
) -> dict:
    """Create a dict acting as a DB row."""
    return {
        "tenant_id": tenant_id,
        "slug": slug,
        "name": name,
        "status": status,
        "plan": plan,
        "config": config,
        "metadata": metadata,
        "created_at": created_at or datetime.now(UTC),
    }


class TestSQLTenantProvider:
    """Tests for SQLTenantProvider."""

    @pytest.mark.asyncio
    async def test_init(self, provider: SQLTenantProvider) -> None:
        """Provider initialises with DB reference."""
        assert provider._db is not None

    @pytest.mark.asyncio
    async def test_get_tenant_returns_none_when_not_found(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Returns None when no row matches."""
        ctx = mock_db.scoped_context.return_value
        ctx.fetch_one = AsyncMock(return_value=None)
        result = await provider.get_tenant("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_tenant_returns_tenant_info(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Returns TenantInfo when row found."""
        ctx = mock_db.scoped_context.return_value
        row = _make_row(tenant_id="t1", slug="test", name="Test")
        ctx.fetch_one = AsyncMock(return_value=row)
        result = await provider.get_tenant("t1")
        assert result is not None
        assert result.tenant_id == "t1"
        assert result.slug == "test"
        assert result.name == "Test"
        assert result.status == TenantStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_get_tenant_by_slug_returns_none_when_not_found(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Returns None when slug not found."""
        ctx = mock_db.scoped_context.return_value
        ctx.fetch_one = AsyncMock(return_value=None)
        result = await provider.get_tenant_by_slug("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_tenant_by_slug_returns_tenant(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Returns TenantInfo when slug matches."""
        ctx = mock_db.scoped_context.return_value
        row = _make_row(tenant_id="t1", slug="my-slug", name="My Tenant")
        ctx.fetch_one = AsyncMock(return_value=row)
        result = await provider.get_tenant_by_slug("my-slug")
        assert result is not None
        assert result.slug == "my-slug"

    @pytest.mark.asyncio
    async def test_list_tenants_returns_empty(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Returns empty list when no tenants."""
        ctx = mock_db.scoped_context.return_value
        ctx.fetch_all = AsyncMock(return_value=[])
        result = await provider.list_tenants()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_tenants_filters_active_only(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Queries with status filter when active_only=True."""
        ctx = mock_db.scoped_context.return_value
        row = _make_row(tenant_id="t1", slug="active-tenant", name="Active")
        ctx.fetch_all = AsyncMock(return_value=[row])
        result = await provider.list_tenants(active_only=True)
        assert len(result) == 1
        assert result[0].slug == "active-tenant"
        executed_sql = ctx.execute.call_args
        # Verify the query had status filter
        call_args = mock_db.scoped_context.return_value.fetch_all.call_args
        assert "status" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_list_tenants_includes_inactive(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Returns all tenants when active_only=False."""
        ctx = mock_db.scoped_context.return_value
        rows = [
            _make_row(tenant_id="t1", slug="active-tenant", name="Active"),
            _make_row(
                tenant_id="t2",
                slug="inactive-tenant",
                name="Inactive",
                status="inactive",
            ),
        ]
        ctx.fetch_all = AsyncMock(return_value=rows)
        result = await provider.list_tenants(active_only=False)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_create_tenant_returns_ok(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Returns Ok with TenantInfo on create."""
        cmd = CreateTenantCommand(slug="new-tenant", name="New Tenant")
        result = await provider.create_tenant(cmd)
        assert result.is_ok()
        info = result.unwrap()
        assert info.slug == "new-tenant"
        assert info.name == "New Tenant"
        assert info.status == TenantStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_create_tenant_generates_unique_id(
        self, provider: SQLTenantProvider
    ) -> None:
        """Each create generates a unique tenant_id."""
        cmd1 = CreateTenantCommand(slug="t1", name="T1")
        cmd2 = CreateTenantCommand(slug="t2", name="T2")
        r1 = (await provider.create_tenant(cmd1)).unwrap()
        r2 = (await provider.create_tenant(cmd2)).unwrap()
        assert r1.tenant_id != r2.tenant_id

    @pytest.mark.asyncio
    async def test_create_tenant_with_plan_and_config(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Create tenant with plan, config, and metadata."""
        cmd = CreateTenantCommand(
            slug="premium",
            name="Premium",
            plan="enterprise",
            config={"max_users": 100},
            metadata={"region": "us-east"},
        )
        result = await provider.create_tenant(cmd)
        assert result.is_ok()
        info = result.unwrap()
        assert info.plan == "enterprise"
        assert info.config == {"max_users": 100}
        assert info.metadata == {"region": "us-east"}

    @pytest.mark.asyncio
    async def test_create_tenant_executes_insert(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Executes INSERT with correct values."""
        cmd = CreateTenantCommand(slug="test", name="Test")
        await provider.create_tenant(cmd)
        ctx = mock_db.scoped_context.return_value
        ctx.execute.assert_awaited_once()
        call_kwargs = ctx.execute.call_args[0][1]
        assert call_kwargs["slug"] == "test"
        assert call_kwargs["name"] == "Test"

    @pytest.mark.asyncio
    async def test_update_tenant_returns_err_when_not_found(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Returns Err when tenant not found."""
        ctx = mock_db.scoped_context.return_value
        ctx.fetch_one = AsyncMock(return_value=None)
        result = await provider.update_tenant(
            "nonexistent", UpdateTenantCommand(name="New Name")
        )
        assert result.is_err()
        assert isinstance(result.unwrap_err(), TenantNotFoundError)

    @pytest.mark.asyncio
    async def test_update_tenant_updates_fields(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Updates fields on existing tenant."""
        ctx = mock_db.scoped_context.return_value
        row = _make_row(
            tenant_id="t1",
            slug="test",
            name="Original",
            plan="basic",
        )
        ctx.fetch_one = AsyncMock(return_value=row)
        result = await provider.update_tenant(
            "t1", UpdateTenantCommand(name="Updated", plan="premium")
        )
        assert result.is_ok()
        info = result.unwrap()
        assert info.name == "Updated"
        assert info.plan == "premium"

    @pytest.mark.asyncio
    async def test_update_tenant_partial(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Partial update preserves existing values."""
        ctx = mock_db.scoped_context.return_value
        row = _make_row(
            tenant_id="t1",
            slug="test",
            name="Original",
            plan="basic",
            config='{"key": "val"}',
        )
        ctx.fetch_one = AsyncMock(return_value=row)
        result = await provider.update_tenant(
            "t1", UpdateTenantCommand(name="Updated")
        )
        assert result.is_ok()
        info = result.unwrap()
        assert info.name == "Updated"
        assert info.plan == "basic"
        assert info.config == {"key": "val"}

    @pytest.mark.asyncio
    async def test_deactivate_tenant_returns_err_when_not_found(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Returns Err when tenant not found."""
        ctx = mock_db.scoped_context.return_value
        ctx.fetch_one = AsyncMock(return_value=None)
        result = await provider.deactivate_tenant("nonexistent")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), TenantNotFoundError)

    @pytest.mark.asyncio
    async def test_deactivate_tenant_sets_status(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Sets status to INACTIVE."""
        ctx = mock_db.scoped_context.return_value
        row = _make_row(tenant_id="t1", slug="test", name="Test")
        ctx.fetch_one = AsyncMock(return_value=row)
        result = await provider.deactivate_tenant("t1")
        assert result.is_ok()
        ctx.execute.assert_awaited_with(
            "UPDATE tenants SET status = :status WHERE tenant_id = :id",
            {"status": "inactive", "id": "t1"},
        )

    @pytest.mark.asyncio
    async def test_activate_tenant_sets_status(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Sets status to ACTIVE."""
        ctx = mock_db.scoped_context.return_value
        row = _make_row(
            tenant_id="t1",
            slug="test",
            name="Test",
            status="inactive",
        )
        ctx.fetch_one = AsyncMock(return_value=row)
        result = await provider.activate_tenant("t1")
        assert result.is_ok()
        ctx.execute.assert_awaited_with(
            "UPDATE tenants SET status = :status WHERE tenant_id = :id",
            {"status": "active", "id": "t1"},
        )

    @pytest.mark.asyncio
    async def test_suspend_tenant_returns_err_when_not_found(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Returns Err when tenant not found."""
        ctx = mock_db.scoped_context.return_value
        ctx.fetch_one = AsyncMock(return_value=None)
        result = await provider.suspend_tenant("nonexistent")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), TenantNotFoundError)

    @pytest.mark.asyncio
    async def test_suspend_tenant_sets_status(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Sets status to SUSPENDED."""
        ctx = mock_db.scoped_context.return_value
        row = _make_row(tenant_id="t1", slug="test", name="Test")
        ctx.fetch_one = AsyncMock(return_value=row)
        result = await provider.suspend_tenant("t1", "violation")
        assert result.is_ok()
        ctx.execute.assert_awaited_with(
            "UPDATE tenants SET status = :status WHERE tenant_id = :id",
            {"status": "suspended", "id": "t1"},
        )

    @pytest.mark.asyncio
    async def test_get_config_returns_none_when_not_set(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Returns None when config key not found."""
        ctx = mock_db.scoped_context.return_value
        ctx.fetch_one = AsyncMock(return_value=None)
        result = await provider.get_config("t1", "missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_config_returns_value(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Returns parsed config value."""
        ctx = mock_db.scoped_context.return_value
        ctx.fetch_one = AsyncMock(return_value={"value": '"hello"'})
        result = await provider.get_config("t1", "greeting")
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_get_all_config_returns_empty(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Returns empty dict when no config rows."""
        ctx = mock_db.scoped_context.return_value
        ctx.fetch_all = AsyncMock(return_value=[])
        result = await provider.get_all_config("t1")
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_all_config_returns_all_keys(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Returns all config key-value pairs."""
        ctx = mock_db.scoped_context.return_value
        rows = [
            {"key": "k1", "value": '"v1"'},
            {"key": "k2", "value": "42"},
        ]
        ctx.fetch_all = AsyncMock(return_value=rows)
        result = await provider.get_all_config("t1")
        assert result == {"k1": "v1", "k2": 42}

    @pytest.mark.asyncio
    async def test_set_config_executes_upsert(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Executes upsert with JSON-dumped value."""
        ctx = mock_db.scoped_context.return_value
        await provider.set_config("t1", "key", {"nested": True})
        ctx.execute.assert_awaited_once()
        call_kwargs = ctx.execute.call_args[0][1]
        assert call_kwargs["id"] == "t1"
        assert call_kwargs["key"] == "key"
        assert call_kwargs["value"] == b'{"nested":true}'

    @pytest.mark.asyncio
    async def test_get_config_handles_tuple_row(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Handles non-dict row types via getattr fallback."""
        ctx = mock_db.scoped_context.return_value

        class TupleRow:
            def __getitem__(self, idx: int) -> str:
                return '"val"' if idx == 0 else ""

        ctx.fetch_one = AsyncMock(return_value=TupleRow())
        result = await provider.get_config("t1", "key")
        assert result == "val"

    @pytest.mark.asyncio
    async def test_get_all_config_handles_tuple_rows(
        self, provider: SQLTenantProvider, mock_db: MagicMock
    ) -> None:
        """Handles non-dict rows for get_all_config."""
        ctx = mock_db.scoped_context.return_value

        class TupleRow:
            def __getitem__(self, idx: int) -> str:
                mapping = {0: "k1", 1: '"v1"'}
                return mapping[idx]

        ctx.fetch_all = AsyncMock(return_value=[TupleRow()])
        result = await provider.get_all_config("t1")
        assert result == {"k1": "v1"}

    @pytest.mark.asyncio
    async def test_row_to_tenant_parses_json_fields(
        self, provider: SQLTenantProvider
    ) -> None:
        """_row_to_tenant parses config and metadata JSON."""
        row = _make_row(
            tenant_id="t1",
            slug="test",
            name="Test",
            config='{"enabled": true}',
            metadata='{"owner": "admin"}',
        )
        tenant = SQLTenantProvider._row_to_tenant(row)
        assert tenant.config == {"enabled": True}
        assert tenant.metadata == {"owner": "admin"}

    @pytest.mark.asyncio
    async def test_row_to_tenant_empty_json_fields(
        self, provider: SQLTenantProvider
    ) -> None:
        """_row_to_tenant handles missing config/metadata."""
        row = _make_row(
            tenant_id="t1",
            slug="test",
            name="Test",
            config=None,
            metadata=None,
        )
        tenant = SQLTenantProvider._row_to_tenant(row)
        assert tenant.config == {}
        assert tenant.metadata == {}


class TestSQLTenantProviderPositionalRow:
    """Tests for _row_to_tenant with positional (non-dict) rows."""

    @pytest.mark.asyncio
    async def test_row_to_tenant_with_mapping_row(self) -> None:
        """Handles row with _mapping attribute (legacy drivers)."""
        row = type("Row", (), {"_mapping": {
            "tenant_id": "t1",
            "slug": "test",
            "name": "Test",
            "status": "active",
            "plan": None,
            "config": '{"a": 1}',
            "metadata": "{}",
            "created_at": None,
        }})()
        tenant = SQLTenantProvider._row_to_tenant(row)
        assert tenant.tenant_id == "t1"
        assert tenant.config == {"a": 1}
