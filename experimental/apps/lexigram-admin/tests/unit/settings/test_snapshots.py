"""Settings changes must be recoverable.

A mistaken save previously could only be undone by remembering the old
values by hand. These tests pin the snapshot/rollback behaviour, including
the rules that stop it from becoming a way to leak secrets or write across
tenant boundaries.
"""

from __future__ import annotations

import pytest

from lexigram.admin.settings.snapshots import (
    InMemorySettingsSnapshotStore,
    SettingsSnapshotService,
)


class TestCapture:
    """Snapshots record the outgoing state, minus secrets."""

    @pytest.mark.asyncio
    async def test_values_are_captured(self) -> None:
        service = SettingsSnapshotService()

        snapshot = await service.capture("admin.cache", {"enabled": "true", "ttl": "60"})

        assert snapshot.values == {"enabled": "true", "ttl": "60"}

    @pytest.mark.asyncio
    async def test_secrets_are_never_captured(self) -> None:
        """A snapshot is operator-readable history; secrets must stay out."""
        service = SettingsSnapshotService()

        snapshot = await service.capture(
            "admin.mail",
            {"host": "smtp.example.com", "api_key": "super-secret"},
            secret_keys={"api_key"},
        )

        assert "api_key" not in snapshot.values
        assert "super-secret" not in str(snapshot.values)

    @pytest.mark.asyncio
    async def test_skipped_secrets_are_reported(self) -> None:
        """Rollback must not silently claim to have restored a secret."""
        service = SettingsSnapshotService()

        snapshot = await service.capture(
            "admin.mail",
            {"host": "h", "api_key": "k"},
            secret_keys={"api_key"},
        )

        assert snapshot.skipped_secrets == ("api_key",)

    @pytest.mark.asyncio
    async def test_actor_and_comment_are_recorded(self) -> None:
        service = SettingsSnapshotService()

        snapshot = await service.capture(
            "admin.cache", {"a": "1"}, actor_id="user-7", comment="save"
        )

        assert snapshot.actor_id == "user-7"
        assert snapshot.comment == "save"


class TestHistory:
    """History is newest-first, per namespace and tenant, and bounded."""

    @pytest.mark.asyncio
    async def test_newest_first(self) -> None:
        service = SettingsSnapshotService()
        await service.capture("admin.cache", {"n": "1"})
        await service.capture("admin.cache", {"n": "2"})

        history = await service.list_history("admin.cache")

        assert [snap.values["n"] for snap in history] == ["2", "1"]

    @pytest.mark.asyncio
    async def test_namespaces_are_isolated(self) -> None:
        service = SettingsSnapshotService()
        await service.capture("admin.cache", {"n": "1"})
        await service.capture("admin.mail", {"n": "2"})

        assert len(await service.list_history("admin.cache")) == 1

    @pytest.mark.asyncio
    async def test_tenants_are_isolated(self) -> None:
        service = SettingsSnapshotService()
        await service.capture("admin.cache", {"n": "a"}, tenant_id="t1")
        await service.capture("admin.cache", {"n": "b"}, tenant_id="t2")

        history = await service.list_history("admin.cache", "t1")

        assert len(history) == 1
        assert history[0].values["n"] == "a"

    @pytest.mark.asyncio
    async def test_retention_cap_drops_oldest(self) -> None:
        service = SettingsSnapshotService(max_per_namespace=3)
        for index in range(5):
            await service.capture("admin.cache", {"n": str(index)})

        history = await service.list_history("admin.cache")

        assert [snap.values["n"] for snap in history] == ["4", "3", "2"]

    @pytest.mark.asyncio
    async def test_trimmed_snapshots_are_unreachable_by_id(self) -> None:
        """Retention must not leave dangling ids that still resolve."""
        store = InMemorySettingsSnapshotStore(max_per_namespace=1)
        service = SettingsSnapshotService(store)
        first = await service.capture("admin.cache", {"n": "1"})
        await service.capture("admin.cache", {"n": "2"})

        assert await service.get(first.snapshot_id) is None


class TestRollbackValues:
    """Rollback resolves a payload; it never writes on its own."""

    @pytest.mark.asyncio
    async def test_returns_captured_values(self) -> None:
        service = SettingsSnapshotService()
        snapshot = await service.capture("admin.cache", {"enabled": "false"})

        assert await service.rollback_values(snapshot.snapshot_id) == {
            "enabled": "false"
        }

    @pytest.mark.asyncio
    async def test_unknown_id_returns_none(self) -> None:
        service = SettingsSnapshotService()

        assert await service.rollback_values("nope") is None

    @pytest.mark.asyncio
    async def test_namespace_mismatch_is_refused(self) -> None:
        """A guessed id from another namespace must not be applicable."""
        service = SettingsSnapshotService()
        snapshot = await service.capture("admin.mail", {"host": "h"})

        result = await service.rollback_values(
            snapshot.snapshot_id, namespace="admin.cache"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_tenant_mismatch_is_refused(self) -> None:
        """Otherwise a snapshot id would enable a cross-tenant write."""
        service = SettingsSnapshotService()
        snapshot = await service.capture(
            "admin.cache", {"enabled": "false"}, tenant_id="t1"
        )

        result = await service.rollback_values(
            snapshot.snapshot_id, namespace="admin.cache", tenant_id="t2"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_matching_scope_is_allowed(self) -> None:
        service = SettingsSnapshotService()
        snapshot = await service.capture(
            "admin.cache", {"enabled": "false"}, tenant_id="t1"
        )

        result = await service.rollback_values(
            snapshot.snapshot_id, namespace="admin.cache", tenant_id="t1"
        )

        assert result == {"enabled": "false"}

    @pytest.mark.asyncio
    async def test_returned_payload_is_a_copy(self) -> None:
        """Mutating a rollback payload must not corrupt stored history."""
        service = SettingsSnapshotService()
        snapshot = await service.capture("admin.cache", {"enabled": "false"})

        payload = await service.rollback_values(snapshot.snapshot_id)
        assert payload is not None
        payload["enabled"] = "mutated"

        stored = await service.get(snapshot.snapshot_id)
        assert stored is not None
        assert stored.values["enabled"] == "false"
