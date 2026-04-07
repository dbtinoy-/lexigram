from __future__ import annotations

"""Audit + SQL + Web audit trail scenario.

Packages under test: lexigram-audit, lexigram-sql, lexigram-web
Infrastructure: PostgreSQL

Scenario:
1. Boot a minimal application with AuditProvider + SqlProvider + WebProvider.
2. POST /api/v1/resources      → creates resource, audit entry written.
3. PUT  /api/v1/resources/{id} → updates resource, audit entry written.
4. DELETE /api/v1/resources/{id} → deletes resource, audit entry written.
5. Each audit entry contains an HMAC that can be independently verified.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.scenario, pytest.mark.requires_postgres]


class TestAuditTrail:
    """Audit + SQL + Web: every mutating HTTP operation produces a verifiable audit entry.

    Boots a minimal application with AuditProvider + SqlProvider + WebProvider.
    Exercises create, update, and delete operations via HTTP and asserts that
    each produces a tamper-evident audit log entry in PostgreSQL.
    """

    @pytest.fixture
    async def bed(self) -> None:
        """Boot a minimal Audit + SQL + Web test application.

        Yields:
            AppTestBed configured with AuditProvider + SqlProvider + WebProvider.
        """
        pytest.skip(
            "TODO: implement create_audit_app factory in conftest.py "
            "and wire AppTestBed.from_factory(create_audit_app)"
        )

    async def test_create_emits_audit_entry(self, bed: object) -> None:
        """A POST request produces exactly one audit entry with action='create'.

        Args:
            bed: Booted AppTestBed with HTTP client and live DB.
        """
        resp = await bed.client.post("/api/v1/resources", json={"name": "audited-resource"})  # type: ignore[attr-defined]
        assert resp.status_code == 201
        resource_id = resp.json()["id"]

        entries = await bed.db.fetch_all(  # type: ignore[attr-defined]
            "SELECT action FROM audit_log WHERE resource_id = $1", resource_id
        )
        assert len(entries) == 1
        assert entries[0]["action"] == "create"

    async def test_update_emits_audit_entry(self, bed: object) -> None:
        """A PUT request produces an audit entry with action='update'.

        Args:
            bed: Booted AppTestBed with HTTP client and live DB.
        """
        resp = await bed.client.post("/api/v1/resources", json={"name": "to-update"})  # type: ignore[attr-defined]
        assert resp.status_code == 201
        resource_id = resp.json()["id"]

        put = await bed.client.put(f"/api/v1/resources/{resource_id}", json={"name": "updated"})  # type: ignore[attr-defined]
        assert put.status_code == 200

        entries = await bed.db.fetch_all(  # type: ignore[attr-defined]
            "SELECT action FROM audit_log WHERE resource_id = $1 ORDER BY created_at",
            resource_id,
        )
        assert len(entries) == 2
        assert entries[-1]["action"] == "update"

    async def test_delete_emits_audit_entry(self, bed: object) -> None:
        """A DELETE request produces an audit entry with action='delete'.

        Args:
            bed: Booted AppTestBed with HTTP client and live DB.
        """
        resp = await bed.client.post("/api/v1/resources", json={"name": "to-delete"})  # type: ignore[attr-defined]
        assert resp.status_code == 201
        resource_id = resp.json()["id"]

        delete = await bed.client.delete(f"/api/v1/resources/{resource_id}")  # type: ignore[attr-defined]
        assert delete.status_code == 204

        entries = await bed.db.fetch_all(  # type: ignore[attr-defined]
            "SELECT action FROM audit_log WHERE resource_id = $1 ORDER BY created_at",
            resource_id,
        )
        assert any(e["action"] == "delete" for e in entries)

    async def test_audit_entry_hmac_verifiable(self, bed: object) -> None:
        """Every audit entry carries an HMAC that can be independently re-computed.

        The HMAC covers the canonical payload so that any post-write tampering
        of the audit row is detectable.

        Args:
            bed: Booted AppTestBed with HTTP client, live DB, and audit verifier.
        """
        resp = await bed.client.post("/api/v1/resources", json={"name": "hmac-resource"})  # type: ignore[attr-defined]
        assert resp.status_code == 201
        resource_id = resp.json()["id"]

        entry = await bed.db.fetch_one(  # type: ignore[attr-defined]
            "SELECT * FROM audit_log WHERE resource_id = $1", resource_id
        )
        assert entry is not None

        is_valid = await bed.audit.verify_hmac(entry)  # type: ignore[attr-defined]
        assert is_valid, "Audit entry HMAC verification failed"
