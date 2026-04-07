from __future__ import annotations

"""Tenancy + SQL + Web multi-tenant data isolation scenario.

Packages under test: lexigram-tenancy, lexigram-sql, lexigram-web
Infrastructure: PostgreSQL

Scenario:
1. Boot a minimal application with TenancyProvider + SqlProvider + WebProvider.
2. Tenant A creates a resource via POST.
3. Tenant B creates a different resource via POST.
4. GET  /api/v1/resources (as Tenant A) → returns only Tenant A's resource.
5. GET  /api/v1/resources (as Tenant B) → returns only Tenant B's resource.
6. GET  /api/v1/resources/{tenant_a_id} (as Tenant B) → 404 Not Found.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.scenario, pytest.mark.requires_postgres]


class TestTenancyIsolation:
    """Tenancy + SQL + Web: strict per-tenant data isolation over real PostgreSQL.

    Boots a minimal multi-tenant application with TenancyProvider + SqlProvider
    + WebProvider, creates resources under two distinct tenants, and verifies
    that each tenant's HTTP client is unable to observe the other's data.
    """

    @pytest.fixture
    async def bed(self) -> None:
        """Boot a minimal Tenancy + SQL + Web test application.

        Yields:
            AppTestBed configured with TenancyProvider + SqlProvider + WebProvider,
            pre-seeded with two tenant contexts (tenant_a_client, tenant_b_client).
        """
        pytest.skip(
            "TODO: implement create_tenancy_app factory in conftest.py "
            "and wire AppTestBed.from_factory(create_tenancy_app)"
        )

    async def test_tenant_a_cannot_see_tenant_b_data(self, bed: object) -> None:
        """Tenant A's list endpoint does not include resources owned by Tenant B.

        Args:
            bed: Booted AppTestBed with two isolated tenant HTTP clients.
        """
        resp_b = await bed.tenant_b_client.post("/api/v1/resources", json={"name": "b-resource"})  # type: ignore[attr-defined]
        assert resp_b.status_code == 201
        b_id = resp_b.json()["id"]

        resp_a = await bed.tenant_a_client.get("/api/v1/resources")  # type: ignore[attr-defined]
        assert resp_a.status_code == 200
        ids = [r["id"] for r in resp_a.json()["items"]]
        assert b_id not in ids

    async def test_tenant_b_cannot_see_tenant_a_data(self, bed: object) -> None:
        """Tenant B's list endpoint does not include resources owned by Tenant A.

        Args:
            bed: Booted AppTestBed with two isolated tenant HTTP clients.
        """
        resp_a = await bed.tenant_a_client.post("/api/v1/resources", json={"name": "a-resource"})  # type: ignore[attr-defined]
        assert resp_a.status_code == 201
        a_id = resp_a.json()["id"]

        resp_b = await bed.tenant_b_client.get("/api/v1/resources")  # type: ignore[attr-defined]
        assert resp_b.status_code == 200
        ids = [r["id"] for r in resp_b.json()["items"]]
        assert a_id not in ids

    async def test_cross_tenant_access_returns_404(self, bed: object) -> None:
        """Fetching another tenant's resource by ID returns 404, not 403.

        Returning 404 instead of 403 avoids leaking whether the resource
        exists at all, which is the correct security posture for multi-tenant
        systems (tenant-ID-scoped queries simply find nothing).

        Args:
            bed: Booted AppTestBed with two isolated tenant HTTP clients.
        """
        resp_a = await bed.tenant_a_client.post("/api/v1/resources", json={"name": "private"})  # type: ignore[attr-defined]
        assert resp_a.status_code == 201
        a_id = resp_a.json()["id"]

        # Tenant B attempts to read Tenant A's resource directly by ID.
        resp = await bed.tenant_b_client.get(f"/api/v1/resources/{a_id}")  # type: ignore[attr-defined]
        assert resp.status_code == 404
