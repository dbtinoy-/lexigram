"""Audit + SQL + Web audit trail scenario.

Packages under test: lexigram-audit, lexigram-sql, lexigram-web
Infrastructure: in-memory SQLite (no live service required)

Scenario:
1. Boot a minimal application with AuditModule + DatabaseModule + WebModule.
2. POST /api/v1/resources      -> creates resource, audit entry written.
3. PUT  /api/v1/resources/{id} -> updates resource, audit entry written.
4. DELETE /api/v1/resources/{id} -> deletes resource, audit entry written.
5. Each audit entry contains an HMAC that can be independently verified.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.integration.scenarios._bed import scenario_bed
from tests.integration.scenarios.scenario_apps import create_audit_app

if TYPE_CHECKING:
    from tests.integration.scenarios._bed import ScenarioTestBed

pytestmark = [pytest.mark.integration, pytest.mark.scenario]


@pytest.fixture
async def bed() -> ScenarioTestBed:
    """Boot a minimal Audit + SQL + Web test application."""
    async with scenario_bed(create_audit_app) as scenario:
        yield scenario


class TestAuditTrail:
    """Audit + SQL + Web: every mutating HTTP operation produces a verifiable entry."""

    async def test_create_emits_audit_entry(self, bed: ScenarioTestBed) -> None:
        """A POST request produces exactly one audit entry with action='resource.create'."""
        resp = await bed.client.post(
            "/api/v1/resources", json={"name": "audited-resource"}
        )
        assert resp.status_code == 201
        resource_id = str(resp.json()["id"])

        entries = await bed.audit.entries(resource_id)
        assert len(entries) == 1
        assert entries[0].action == "resource.create"

    async def test_update_emits_audit_entry(self, bed: ScenarioTestBed) -> None:
        """A PUT request produces an audit entry with action='resource.update'."""
        resp = await bed.client.post(
            "/api/v1/resources", json={"name": "to-update"}
        )
        assert resp.status_code == 201
        resource_id = str(resp.json()["id"])

        put = await bed.client.put(
            f"/api/v1/resources/{resource_id}", json={"name": "updated"}
        )
        assert put.status_code == 200

        entries = await bed.audit.entries(resource_id)
        actions = {e.action for e in entries}
        assert actions == {"resource.create", "resource.update"}

    async def test_delete_emits_audit_entry(self, bed: ScenarioTestBed) -> None:
        """A DELETE request produces an audit entry with action='resource.delete'."""
        resp = await bed.client.post(
            "/api/v1/resources", json={"name": "to-delete"}
        )
        assert resp.status_code == 201
        resource_id = str(resp.json()["id"])

        delete = await bed.client.delete(f"/api/v1/resources/{resource_id}")
        assert delete.status_code == 204

        entries = await bed.audit.entries(resource_id)
        assert any(e.action == "resource.delete" for e in entries)

    async def test_audit_entry_hmac_verifiable(self, bed: ScenarioTestBed) -> None:
        """Every audit entry carries an HMAC that can be independently re-computed."""
        resp = await bed.client.post(
            "/api/v1/resources", json={"name": "hmac-resource"}
        )
        assert resp.status_code == 201
        resource_id = str(resp.json()["id"])

        entries = await bed.audit.entries(resource_id)
        assert entries
        assert await bed.audit.verify(entries[0])
