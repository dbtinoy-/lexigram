"""Tenancy + SQL + Web multi-tenant data isolation scenario.

Packages under test: lexigram-tenancy, lexigram-sql, lexigram-web
Infrastructure: in-memory SQLite (no live service required)

Scenario:
1. Boot a minimal application with TenancyModule + DatabaseModule + WebModule.
2. Tenant A creates a resource via POST.
3. Tenant B creates a different resource via POST.
4. GET  /api/v1/resources (as Tenant A) -> returns only Tenant A's resource.
5. GET  /api/v1/resources (as Tenant B) -> returns only Tenant B's resource.
6. GET  /api/v1/resources/{tenant_a_id} (as Tenant B) -> 404 Not Found.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.integration.scenarios._bed import scenario_bed
from tests.integration.scenarios.scenario_apps import create_tenancy_app

if TYPE_CHECKING:
    from tests.integration.scenarios._bed import ScenarioTestBed

pytestmark = [pytest.mark.integration, pytest.mark.scenario]


@pytest.fixture
async def bed() -> "ScenarioTestBed":
    """Boot a minimal Tenancy + SQL + Web test application."""
    async with scenario_bed(create_tenancy_app) as scenario:
        yield scenario


class TestTenancyIsolation:
    """Tenancy + SQL + Web: strict per-tenant data isolation."""

    async def test_tenant_a_cannot_see_tenant_b_data(
        self, bed: "ScenarioTestBed"
    ) -> None:
        """Tenant A's list endpoint does not include resources owned by Tenant B."""
        resp_b = await bed.client.post(
            "/api/v1/resources",
            json={"name": "b-resource"},
            headers={"X-Tenant-ID": "tenant-b"},
        )
        assert resp_b.status_code == 201
        b_id = resp_b.json()["id"]

        resp_a = await bed.client.get(
            "/api/v1/resources", headers={"X-Tenant-ID": "tenant-a"}
        )
        assert resp_a.status_code == 200
        ids = [r["id"] for r in resp_a.json()["items"]]
        assert b_id not in ids

    async def test_tenant_b_cannot_see_tenant_a_data(
        self, bed: "ScenarioTestBed"
    ) -> None:
        """Tenant B's list endpoint does not include resources owned by Tenant A."""
        resp_a = await bed.client.post(
            "/api/v1/resources",
            json={"name": "a-resource"},
            headers={"X-Tenant-ID": "tenant-a"},
        )
        assert resp_a.status_code == 201
        a_id = resp_a.json()["id"]

        resp_b = await bed.client.get(
            "/api/v1/resources", headers={"X-Tenant-ID": "tenant-b"}
        )
        assert resp_b.status_code == 200
        ids = [r["id"] for r in resp_b.json()["items"]]
        assert a_id not in ids

    async def test_cross_tenant_access_returns_404(self, bed: "ScenarioTestBed") -> None:
        """Fetching another tenant's resource by ID returns 404, not 403."""
        resp_a = await bed.client.post(
            "/api/v1/resources",
            json={"name": "private"},
            headers={"X-Tenant-ID": "tenant-a"},
        )
        assert resp_a.status_code == 201
        a_id = resp_a.json()["id"]

        resp = await bed.client.get(
            f"/api/v1/resources/{a_id}", headers={"X-Tenant-ID": "tenant-b"}
        )
        assert resp.status_code == 404
