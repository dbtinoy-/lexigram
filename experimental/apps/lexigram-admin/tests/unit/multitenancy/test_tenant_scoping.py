"""Server-side tenant scoping contract tests.

Layer 1: ``resolve_tenant_id`` must never honor a client-supplied tenant that
differs from the authenticated claim (when a claim exists) or the registry.
Layer 2: ``RepositoryDataSource`` with a ``tenant_scope`` set must inject a
mandatory ``tenant_id`` filter on reads and refuse cross-tenant writes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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

    async def find_many(self, **kwargs):
        self.find_many_calls.append(kwargs)
        return _Result()

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
async def test_cross_tenant_read_returns_none():
    from lexigram.admin.data.adapters.repository.data_source import (
        RepositoryDataSource,
    )

    repo = _RecordingRepo()  # find_by_id returns tenant_id="other"
    ds = RepositoryDataSource(repository=repo, tenant_scope="acme")
    assert await ds.find_one("1") is None


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
async def test_no_scope_keeps_passthrough():
    from lexigram.admin.data.adapters.repository.data_source import (
        RepositoryDataSource,
    )

    repo = _RecordingRepo()
    ds = RepositoryDataSource(repository=repo)
    await ds.create({"name": "x"})
    assert "tenant_id" not in repo.created[-1]
