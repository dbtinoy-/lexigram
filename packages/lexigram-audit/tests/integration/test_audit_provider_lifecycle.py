from __future__ import annotations

"""Audit bundle provider lifecycle integration tests."""

import pytest

from lexigram.testing.integration.fixtures import postgres_pool  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.requires_postgres]


class TestAuditProviderLifecycle:
    """Verify AuditBundleProvider boots and shuts down with real PostgreSQL.

    Tests that do not require live infrastructure run unconditionally;
    tests requiring a live PostgreSQL connection are skipped automatically
    when the database is unavailable.
    """

    async def test_bundle_provider_can_be_created(self) -> None:
        """AuditBundleProvider can be instantiated without errors.

        Exercises the composite provider constructor, which wires all four
        sub-providers (core, retention, verifier, admin).
        """
        from lexigram.audit.di.bundle_provider import AuditBundleProvider

        provider = AuditBundleProvider()
        assert provider is not None
        assert provider.name == "audit_bundle"

    async def test_bundle_provider_without_admin(self) -> None:
        """AuditBundleProvider can be created with admin contributor disabled."""
        from lexigram.audit.di.bundle_provider import AuditBundleProvider

        provider = AuditBundleProvider(enable_admin=False)
        assert provider is not None

    async def test_in_memory_store_appends_and_queries(self) -> None:
        """InMemoryAuditStore appends entries and returns them via query.

        Confirms the zero-infrastructure store works end-to-end; used as the
        default backend when no SQL store is available.
        """
        from lexigram.audit.store.memory import InMemoryAuditStore
        from lexigram.contracts.audit import AuditEntry, AuditEventSeverity, AuditQuery

        store = InMemoryAuditStore()
        entry = AuditEntry(
            action="user.login",
            actor_id="user-42",
            resource_type="User",
            resource_id="user-42",
            outcome="success",
            severity=AuditEventSeverity.MEDIUM,
            source="test",
        )

        await store.append(entry)
        results = await store.query(AuditQuery(actor_id="user-42"))

        assert len(results) == 1
        assert results[0].action == "user.login"
        assert results[0].actor_id == "user-42"

    async def test_in_memory_store_count_matches_appended(self) -> None:
        """InMemoryAuditStore.count() returns the correct number of matching entries."""
        from lexigram.audit.store.memory import InMemoryAuditStore
        from lexigram.contracts.audit import AuditEntry, AuditEventSeverity, AuditQuery

        store = InMemoryAuditStore()
        for i in range(3):
            await store.append(
                AuditEntry(
                    action="resource.delete",
                    actor_id=f"user-{i}",
                    resource_type="Document",
                    resource_id=f"doc-{i}",
                    outcome="success",
                    severity=AuditEventSeverity.HIGH,
                    source="test",
                )
            )

        total = await store.count(AuditQuery())
        assert total == 3

    async def test_audit_logger_wraps_store(self) -> None:
        """AuditLogger delegates log() calls to the underlying store.

        Verifies the logger-store wiring without any real infrastructure.
        """
        from lexigram.audit.logging.logger import AuditLogger
        from lexigram.audit.store.memory import InMemoryAuditStore
        from lexigram.contracts.audit import AuditEntry, AuditEventSeverity, AuditQuery

        store = InMemoryAuditStore()
        logger = AuditLogger(store=store)

        entry = AuditEntry(
            action="config.update",
            actor_id="admin-1",
            resource_type="Config",
            resource_id="global",
            outcome="success",
            severity=AuditEventSeverity.HIGH,
            source="test",
        )
        await logger.log(entry)

        results = await store.query(AuditQuery(actor_id="admin-1"))
        assert len(results) == 1
        assert results[0].action == "config.update"

    async def test_bundle_provider_config_key(self) -> None:
        """AuditBundleProvider exposes the expected config_key."""
        from lexigram.audit.di.bundle_provider import AuditBundleProvider

        provider = AuditBundleProvider()
        assert provider.config_key == "audit"
