"""Server-side tenant scoping contract tests.

Layer 1: ``resolve_tenant_id`` must never honor a client-supplied tenant that
differs from the authenticated claim (when a claim exists) or the registry.
Layer 2: ``RepositoryDataSource`` with a ``tenant_scope`` set must inject a
mandatory ``tenant_id`` filter on reads and refuse cross-tenant writes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Layer 1 — identity-bound resolution
# ---------------------------------------------------------------------------


async def test_header_matching_claim_is_honored():
    from lexigram.admin.multitenancy.adapter import resolve_tenant_id

    class _Req:
        headers = {"X-Tenant-Id": "acme"}
        state = type("S", (), {"tenant_id": None})()

    assert await resolve_tenant_id(_Req(), claim="acme") == "acme"


async def test_header_conflicting_with_claim_is_rejected():
    from lexigram.admin.multitenancy.adapter import resolve_tenant_id

    class _Req:
        headers = {"X-Tenant-Id": "evil"}
        state = type("S", (), {"tenant_id": None})()

    assert await resolve_tenant_id(_Req(), claim="acme") == "acme"


async def test_no_claim_and_no_client_hint_falls_back_to_default():
    from lexigram.admin.multitenancy.adapter import resolve_tenant_id

    class _Req:
        headers: dict = {}
        state = type("S", (), {"tenant_id": None})()

    assert await resolve_tenant_id(_Req(), default="default") == "default"


# ---------------------------------------------------------------------------
# Layer 2 — repository data-source scoping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_mounts_tenant_wrapper_through_resource_contract():
    """Mounted resources must route through Resource.set_data_source()."""
    from lexigram.admin.config import AdminConfig
    from lexigram.admin.di.bundle_provider import AdminProvider
    from lexigram.admin.di.mount.context import MountContext
    from lexigram.admin.multitenancy.data_source import TenantScopedDataSource
    from lexigram.admin.resources.base import Resource

    resource = Resource()
    source = MagicMock()
    resource._data_source = source
    provider = AdminProvider(
        config=AdminConfig.from_dict(
            {
                "tenancy": {
                    "enabled": True,
                    "default_tenant_id": "acme",
                }
            }
        )
    )

    provider._mount_tenant_scoping(MountContext(resources={"users": resource}))

    assert isinstance(resource._data_source, TenantScopedDataSource)
    assert resource._data_source.tenant_id == "acme"


@dataclass
class _Result:
    items: list = field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 20
    has_next: bool = False
    has_prev: bool = False


class _RecordingRepo:
    def __init__(self):
        self.find_many_calls: list[dict] = []
        self.created: list[dict] = []
        self.updated: list[tuple] = []
        self.items: list[dict] = []

    async def find_many(self, **kwargs):
        self.find_many_calls.append(kwargs)
        return list(self.items)

    async def count(self, **kwargs):
        return 0

    async def find_by_id(self, item_id):
        return {"id": item_id, "tenant_id": "other"}

    async def create(self, data):
        self.created.append(data)
        return data

    async def update(self, item_id, data):
        self.updated.append((item_id, data))
        return data

    async def delete(self, item_id):
        return True


@pytest.mark.asyncio
async def test_find_many_injects_tenant_filter():
    from lexigram.admin.data.adapters.repository.data_source import (
        RepositoryDataSource,
    )

    repo = _RecordingRepo()
    ds = RepositoryDataSource(repository=repo, tenant_scope="acme")
    from lexigram.admin.data.query import QuerySpec

    await ds.find_many(QuerySpec())
    filters = repo.find_many_calls[0]["filters"]
    assert filters["tenant_id"] == "acme"


@pytest.mark.asyncio
async def test_find_many_filters_rows_when_repository_ignores_scope():
    from lexigram.admin.data.adapters.repository.data_source import (
        RepositoryDataSource,
    )
    from lexigram.admin.data.query import QuerySpec

    repo = _RecordingRepo()
    repo.items = [
        {"id": "owned", "tenant_id": "acme"},
        {"id": "other", "tenant_id": "beta"},
        {"id": "unscoped"},
    ]
    ds = RepositoryDataSource(repository=repo, tenant_scope="acme")

    result = await ds.find_many(QuerySpec())

    assert [item["id"] for item in result.items] == ["owned"]


@pytest.mark.asyncio
async def test_cross_tenant_read_returns_none():
    from lexigram.admin.data.adapters.repository.data_source import (
        RepositoryDataSource,
    )

    repo = _RecordingRepo()  # find_by_id returns tenant_id="other"
    ds = RepositoryDataSource(repository=repo, tenant_scope="acme")
    assert await ds.find_one("1") is None


@pytest.mark.asyncio
async def test_same_tenant_dict_update_is_allowed():
    from lexigram.admin.data.adapters.repository.data_source import (
        RepositoryDataSource,
    )

    class _SameTenantRepo(_RecordingRepo):
        async def find_by_id(self, item_id):
            return {"id": item_id, "tenant_id": "acme"}

    repo = _SameTenantRepo()
    ds = RepositoryDataSource(repository=repo, tenant_scope="acme")
    await ds.update("1", {"name": "x"})
    assert repo.updated == [("1", {"name": "x", "tenant_id": "acme"})]


@pytest.mark.asyncio
async def test_cross_tenant_update_refused():
    from lexigram.admin.data.adapters.repository.data_source import (
        RepositoryDataSource,
    )

    repo = _RecordingRepo()
    ds = RepositoryDataSource(repository=repo, tenant_scope="acme")
    with pytest.raises(PermissionError, match="tenant"):
        await ds.update("1", {"name": "x"})
    assert repo.updated == []


@pytest.mark.asyncio
async def test_create_stamps_tenant():
    from lexigram.admin.data.adapters.repository.data_source import (
        RepositoryDataSource,
    )

    repo = _RecordingRepo()
    ds = RepositoryDataSource(repository=repo, tenant_scope="acme")
    await ds.create({"name": "x"})
    assert repo.created[-1]["tenant_id"] == "acme"


@pytest.mark.asyncio
async def test_scoped_update_overwrites_tenant_payload():
    from lexigram.admin.data.adapters.repository.data_source import (
        RepositoryDataSource,
    )

    class _ScopedRepo(_RecordingRepo):
        async def find_by_id(self, item_id):
            return {"id": item_id, "tenant_id": "acme"}

    repo = _ScopedRepo()
    ds = RepositoryDataSource(repository=repo, tenant_scope="acme")
    await ds.update("1", {"name": "x", "tenant_id": "other"})
    assert repo.updated[-1][1]["tenant_id"] == "acme"


@pytest.mark.asyncio
async def test_scoped_bulk_create_stamps_each_item():
    from lexigram.admin.data.adapters.repository.data_source import (
        RepositoryDataSource,
    )

    repo = _RecordingRepo()
    ds = RepositoryDataSource(repository=repo, tenant_scope="acme")
    await ds.bulk_create([{"name": "a"}, {"name": "b", "tenant_id": "other"}])
    assert [item["tenant_id"] for item in repo.created] == ["acme", "acme"]


@pytest.mark.asyncio
async def test_no_scope_keeps_passthrough():
    from lexigram.admin.data.adapters.repository.data_source import (
        RepositoryDataSource,
    )

    repo = _RecordingRepo()
    ds = RepositoryDataSource(repository=repo)
    await ds.create({"name": "x"})
    assert "tenant_id" not in repo.created[-1]
