"""Tests for the admin schema-version marker (R15).

Includes the DDL staleness guard: if any auth-store DDL changes without
updating ADMIN_AUTH_SCHEMA_FINGERPRINT, the guard fails and prints the
new fingerprint to copy into the constant.
"""

from __future__ import annotations

import pytest

from lexigram.admin.auth.store.schema_marker import (
    ADMIN_AUTH_SCHEMA_FINGERPRINT,
    AUTH_STORES_COMPONENT,
    SCHEMA_SOURCE_MODULES,
    AdminSchemaMarker,
    compute_schema_fingerprint,
)


class _Result:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows


class FakeDb:
    """Minimal db provider stub backing the marker with a dict."""

    database_type = "sqlite"

    def __init__(self) -> None:
        self.markers: dict[str, str] = {}
        self.executed: list[str] = []
        self.fail_next = False

    async def execute(self, sql: str, params: list) -> None:
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("db down")
        self.executed.append(sql.strip().split()[0].upper() + ":" + sql.strip()[:40])
        if sql.strip().upper().startswith("INSERT"):
            component, fingerprint = params
            self.markers[component] = fingerprint

    async def execute_query(self, sql: str, params: list) -> _Result:
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("db down")
        component = params[0]
        if component in self.markers:
            return _Result([{"fingerprint": self.markers[component]}])
        return _Result([])


# ============================================================================
# Fingerprint staleness guard
# ============================================================================


class TestSchemaFingerprint:
    def test_fingerprint_constant_is_current(self) -> None:
        """DDL changed? Update ADMIN_AUTH_SCHEMA_FINGERPRINT to the value below.

        The constant must track the stores' DDL so deployed markers are
        invalidated on upgrade. This guard recomputes the fingerprint from
        source and fails with the new value when they diverge.
        """
        computed = compute_schema_fingerprint()
        assert computed == ADMIN_AUTH_SCHEMA_FINGERPRINT, (
            "Auth-store DDL changed. Update ADMIN_AUTH_SCHEMA_FINGERPRINT in "
            "src/lexigram/admin/auth/store/schema_marker.py to: " + computed
        )

    def test_fingerprint_is_hex_sha256(self) -> None:
        assert len(ADMIN_AUTH_SCHEMA_FINGERPRINT) == 64
        int(ADMIN_AUTH_SCHEMA_FINGERPRINT, 16)  # raises if not hex

    def test_every_module_contributes_ddl(self) -> None:
        """Each scanned module must yield at least one DDL literal."""
        for module in SCHEMA_SOURCE_MODULES:
            # Raises ValueError when a module contributes nothing.
            compute_schema_fingerprint((module,))

    def test_module_without_ddl_raises(self) -> None:
        with pytest.raises(ValueError, match="no DDL literals"):
            compute_schema_fingerprint(("lexigram.admin.sql_dialect",))

    def test_fingerprint_is_deterministic(self) -> None:
        assert compute_schema_fingerprint() == compute_schema_fingerprint()


# ============================================================================
# AdminSchemaMarker behaviour
# ============================================================================


class TestAdminSchemaMarker:
    @pytest.mark.asyncio
    async def test_not_current_when_no_row(self) -> None:
        marker = AdminSchemaMarker(FakeDb())
        assert await marker.is_current(AUTH_STORES_COMPONENT, "abc") is False

    @pytest.mark.asyncio
    async def test_mark_then_is_current_roundtrip(self) -> None:
        db = FakeDb()
        marker = AdminSchemaMarker(db)
        await marker.mark_current(AUTH_STORES_COMPONENT, "abc")
        assert await marker.is_current(AUTH_STORES_COMPONENT, "abc") is True

    @pytest.mark.asyncio
    async def test_stale_fingerprint_is_not_current(self) -> None:
        db = FakeDb()
        marker = AdminSchemaMarker(db)
        await marker.mark_current(AUTH_STORES_COMPONENT, "old")
        assert await marker.is_current(AUTH_STORES_COMPONENT, "new") is False

    @pytest.mark.asyncio
    async def test_upsert_overwrites(self) -> None:
        db = FakeDb()
        marker = AdminSchemaMarker(db)
        await marker.mark_current(AUTH_STORES_COMPONENT, "old")
        await marker.mark_current(AUTH_STORES_COMPONENT, "new")
        assert await marker.is_current(AUTH_STORES_COMPONENT, "new") is True

    @pytest.mark.asyncio
    async def test_components_are_independent(self) -> None:
        db = FakeDb()
        marker = AdminSchemaMarker(db)
        await marker.mark_current("admin.auth_stores", "abc")
        assert await marker.is_current("admin.other", "abc") is False

    @pytest.mark.asyncio
    async def test_marker_table_created_once(self) -> None:
        db = FakeDb()
        marker = AdminSchemaMarker(db)
        await marker.is_current(AUTH_STORES_COMPONENT, "abc")
        await marker.is_current(AUTH_STORES_COMPONENT, "abc")
        creates = [s for s in db.executed if s.startswith("CREATE")]
        assert len(creates) == 1

    @pytest.mark.asyncio
    async def test_db_errors_propagate_to_caller(self) -> None:
        """The boot loop treats any marker exception as 'not current'."""
        db = FakeDb()
        db.fail_next = True
        marker = AdminSchemaMarker(db)
        with pytest.raises(RuntimeError, match="db down"):
            await marker.is_current(AUTH_STORES_COMPONENT, "abc")

    @pytest.mark.asyncio
    async def test_empty_stored_fingerprint_is_not_current(self) -> None:
        db = FakeDb()
        marker = AdminSchemaMarker(db)
        db.markers[AUTH_STORES_COMPONENT] = ""
        assert await marker.is_current(AUTH_STORES_COMPONENT, "") is False
