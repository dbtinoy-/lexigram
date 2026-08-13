from __future__ import annotations

from typing import Any

import pytest

from lexigram.secrets.audit import SecretAuditDecorator
from lexigram.testing.fakes import FakeRotatableSecretStore


class FakeAuditLogger:
    """In-memory audit logger for testing."""

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    async def log(self, entry: Any) -> None:  # noqa: ANN401
        self.entries.append({
            "action": entry.action,
            "actor_id": entry.actor_id,
            "resource_type": entry.resource_type,
            "resource_id": entry.resource_id,
        })


class TestSecretAuditDecorator:
    @pytest.fixture
    def store(self) -> FakeRotatableSecretStore:
        return FakeRotatableSecretStore()

    @pytest.fixture
    def logger(self) -> FakeAuditLogger:
        return FakeAuditLogger()

    @pytest.fixture
    def audited(
        self,
        store: FakeRotatableSecretStore,
        logger: FakeAuditLogger,
    ) -> SecretAuditDecorator:
        return SecretAuditDecorator(store, logger)

    async def test_get_logs_entry(
        self,
        audited: SecretAuditDecorator,
        logger: FakeAuditLogger,
    ) -> None:
        await audited.set("key", "val")
        result = await audited.get("key")
        assert result == "val"
        actions = [e["action"] for e in logger.entries]
        assert "secret.get" in actions

    async def test_set_logs_entry(
        self,
        audited: SecretAuditDecorator,
        logger: FakeAuditLogger,
    ) -> None:
        await audited.set("key", "val")
        assert any(e["action"] == "secret.set" for e in logger.entries)

    async def test_delete_logs_entry(
        self,
        audited: SecretAuditDecorator,
        logger: FakeAuditLogger,
    ) -> None:
        await audited.set("key", "val")
        await audited.delete("key")
        assert any(e["action"] == "secret.delete" for e in logger.entries)

    async def test_rotate_logs_entry(
        self,
        audited: SecretAuditDecorator,
        logger: FakeAuditLogger,
    ) -> None:
        await audited.set("key", "val")
        await audited.rotate("key")
        assert any(e["action"] == "secret.rotate" for e in logger.entries)

    async def test_audit_actor_id_default(
        self,
        store: FakeRotatableSecretStore,
        logger: FakeAuditLogger,
    ) -> None:
        audited = SecretAuditDecorator(store, logger)
        await audited.set("key", "val")
        assert logger.entries[0]["actor_id"] == "secrets-system"

    async def test_audit_custom_actor_id(
        self,
        store: FakeRotatableSecretStore,
        logger: FakeAuditLogger,
    ) -> None:
        audited = SecretAuditDecorator(store, logger, actor_id="custom-bot")
        await audited.set("key", "val")
        assert logger.entries[0]["actor_id"] == "custom-bot"

    async def test_get_bulk_logs(
        self,
        audited: SecretAuditDecorator,
        logger: FakeAuditLogger,
    ) -> None:
        await audited.set("a", "1")
        await audited.set("b", "2")
        result = await audited.get_bulk("a", "b")
        assert result == {"a": "1", "b": "2"}
        assert len([e for e in logger.entries if e["action"] == "secret.get"]) == 2

    async def test_get_version_logs(
        self,
        audited: SecretAuditDecorator,
        logger: FakeAuditLogger,
    ) -> None:
        await audited.set("key", "v1")
        result = await audited.get_version("key", 1)
        assert result == "v1"
        assert any(e["action"] == "secret.get_version" for e in logger.entries)

    async def test_list_versions_logs(
        self,
        audited: SecretAuditDecorator,
        logger: FakeAuditLogger,
    ) -> None:
        await audited.set("key", "v1")
        versions = await audited.list_versions("key")
        assert len(versions) == 1
        assert any(e["action"] == "secret.list_versions" for e in logger.entries)

    async def test_get_current_version_logs(
        self,
        audited: SecretAuditDecorator,
        logger: FakeAuditLogger,
    ) -> None:
        await audited.set("key", "val")
        result = await audited.get_current_version("key")
        assert str(result.value) == "val"
        assert any(e["action"] == "secret.get_current_version" for e in logger.entries)

    async def test_entry_has_resource_type(
        self,
        audited: SecretAuditDecorator,
        logger: FakeAuditLogger,
    ) -> None:
        await audited.set("key", "val")
        assert logger.entries[0]["resource_type"] == "secret"
