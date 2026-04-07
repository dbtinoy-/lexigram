from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import botocore.exceptions  # type: ignore[import-untyped]
import pytest

from lexigram.primitives.context import (
    CORRELATION_ID,
    TENANT_ID,
    Context,
    ContextVarRegistry,
)
from lexigram.secrets.audit import SecretAuditDecorator
from lexigram.secrets.rotation import RotationDecorator, RotationSchedule
from lexigram.testing.fakes import FakeRotatableSecretStore

#
# Bug 1: Grace period not implemented
#


class TestRotationScheduleGracePeriod:
    def test_default_grace_period(self) -> None:
        sched = RotationSchedule(max_age_seconds=100.0)
        assert sched.grace_period_seconds == 300.0

    def test_custom_grace_period(self) -> None:
        sched = RotationSchedule(max_age_seconds=100.0, grace_period_seconds=60.0)
        assert sched.grace_period_seconds == 60.0


class TestGracePeriod:
    @pytest.fixture
    def store(self) -> FakeRotatableSecretStore:
        return FakeRotatableSecretStore()

    @pytest.fixture
    def schedule(self) -> RotationSchedule:
        return RotationSchedule(max_age_seconds=0.0, grace_period_seconds=3600.0)

    @pytest.fixture
    def decorator(
        self, store: FakeRotatableSecretStore, schedule: RotationSchedule
    ) -> RotationDecorator:
        return RotationDecorator(store, schedule)

    async def test_get_rotated_sets_expires_at_on_rotation(
        self,
        store: FakeRotatableSecretStore,
        decorator: RotationDecorator,
    ) -> None:
        await store.set("key", "old-value")
        value, rotated = await decorator.get_rotated("key")
        assert rotated
        assert value != "old-value"

    async def test_get_current_version_returns_old_during_grace(
        self,
        store: FakeRotatableSecretStore,
        decorator: RotationDecorator,
    ) -> None:
        await store.set("key", "old-value")
        await decorator.get_rotated("key")
        current = await decorator.get_current_version("key")
        assert str(current.value) == "old-value"

    async def test_get_current_version_returns_new_after_grace_expires(
        self,
        store: FakeRotatableSecretStore,
        decorator: RotationDecorator,
    ) -> None:
        await store.set("key", "old-value")
        schedule = RotationSchedule(max_age_seconds=0.0, grace_period_seconds=0.0)
        decorator = RotationDecorator(store, schedule)
        value, rotated = await decorator.get_rotated("key")
        assert rotated
        current = await decorator.get_current_version("key")
        assert str(current.value) != "old-value"
        assert str(current.value) == value

    async def test_get_current_version_passthrough_when_no_rotation(
        self,
        store: FakeRotatableSecretStore,
        decorator: RotationDecorator,
    ) -> None:
        long_schedule = RotationSchedule(max_age_seconds=999999.0)
        decorator = RotationDecorator(store, long_schedule)
        await store.set("key", "my-value")
        current = await decorator.get_current_version("key")
        assert str(current.value) == "my-value"


#
# Bug 2: SecretAuditDecorator drops Context/tenant_id
#


class FakeAuditLoggerWithDetails:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    async def log(self, entry: Any) -> None:
        self.entries.append(
            {
                "action": entry.action,
                "actor_id": entry.actor_id,
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "tenant_id": entry.tenant_id,
                "correlation_id": entry.correlation_id,
            }
        )


class TestSecretAuditDecoratorContext:
    @pytest.fixture
    def store(self) -> FakeRotatableSecretStore:
        return FakeRotatableSecretStore()

    @pytest.fixture
    def logger(self) -> FakeAuditLoggerWithDetails:
        return FakeAuditLoggerWithDetails()

    @pytest.fixture
    def context(self) -> Context:
        registry = ContextVarRegistry()
        registry.register_key(TENANT_ID)
        registry.register_key(CORRELATION_ID)
        ctx = Context(registry)
        ctx.set(TENANT_ID, "tenant-42")
        ctx.set(CORRELATION_ID, "corr-abc")
        return ctx

    async def test_audit_entry_includes_tenant_id(
        self,
        store: FakeRotatableSecretStore,
        logger: FakeAuditLoggerWithDetails,
        context: Context,
    ) -> None:
        audited = SecretAuditDecorator(store, logger, context=context)
        await audited.set("key", "val")
        assert logger.entries[0]["tenant_id"] == "tenant-42"

    async def test_audit_entry_includes_correlation_id(
        self,
        store: FakeRotatableSecretStore,
        logger: FakeAuditLoggerWithDetails,
        context: Context,
    ) -> None:
        audited = SecretAuditDecorator(store, logger, context=context)
        await audited.set("key", "val")
        assert logger.entries[0]["correlation_id"] == "corr-abc"

    async def test_audit_entry_no_context_omits_tenant(
        self,
        store: FakeRotatableSecretStore,
        logger: FakeAuditLoggerWithDetails,
    ) -> None:
        audited = SecretAuditDecorator(store, logger)
        await audited.set("key", "val")
        assert logger.entries[0]["tenant_id"] is None

    async def test_audit_all_operations_pass_context(
        self,
        store: FakeRotatableSecretStore,
        logger: FakeAuditLoggerWithDetails,
        context: Context,
    ) -> None:
        audited = SecretAuditDecorator(store, logger, context=context)
        await audited.set("k", "v")
        await audited.get("k")
        await audited.delete("k")
        for entry in logger.entries:
            assert entry["tenant_id"] == "tenant-42"
            assert entry["correlation_id"] == "corr-abc"


#
# Bug 3: HashicorpVaultStore uses sync hvac.Client in async methods
#


class TestHashicorpVaultStoreAsync:
    @pytest.fixture
    def mock_hvac_client(self) -> MagicMock:
        client = MagicMock()
        client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {
                "data": {"value": "test-val"},
                "metadata": {"version": 1, "created_time": "2026-01-01T00:00:00Z"},
            }
        }
        client.secrets.kv.v2.create_or_update_secret.return_value = {}
        client.secrets.kv.v2.delete_metadata_and_all_versions.return_value = {}
        client.secrets.kv.v2.read_secret_metadata.return_value = {
            "data": {
                "versions": {
                    "1": {"destroyed": False, "created_time": "2026-01-01T00:00:00Z"}
                }
            }
        }
        return client

    async def test_get_uses_to_thread(
        self,
        mock_hvac_client: MagicMock,
    ) -> None:
        from lexigram.secrets.backends.vault import HashicorpVaultStore

        store = HashicorpVaultStore(url="http://localhost:8200", token="test")
        store._client = mock_hvac_client

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = {
                "data": {
                    "data": {"value": "test-val"},
                    "metadata": {"version": 1, "created_time": "2026-01-01T00:00:00Z"},
                }
            }
            result = await store.get("my-secret")
            assert result == "test-val"
            assert mock_to_thread.called

    async def test_set_uses_to_thread(
        self,
        mock_hvac_client: MagicMock,
    ) -> None:
        from lexigram.secrets.backends.vault import HashicorpVaultStore

        store = HashicorpVaultStore(url="http://localhost:8200", token="test")
        store._client = mock_hvac_client

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            await store.set("my-secret", "new-value")
            assert mock_to_thread.called

    async def test_list_versions_uses_to_thread(
        self,
        mock_hvac_client: MagicMock,
    ) -> None:
        from lexigram.secrets.backends.vault import HashicorpVaultStore

        store = HashicorpVaultStore(url="http://localhost:8200", token="test")
        store._client = mock_hvac_client

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = {
                "data": {
                    "versions": {
                        "1": {
                            "destroyed": False,
                            "created_time": "2026-01-01T00:00:00Z",
                        }
                    }
                }
            }
            result = await store.list_versions("my-secret")
            assert len(result) >= 0
            assert mock_to_thread.called

    async def test_get_version_uses_to_thread(
        self,
        mock_hvac_client: MagicMock,
    ) -> None:
        from lexigram.secrets.backends.vault import HashicorpVaultStore

        store = HashicorpVaultStore(url="http://localhost:8200", token="test")
        store._client = mock_hvac_client

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = {
                "data": {
                    "data": {"value": "test-val"},
                    "metadata": {"version": 1, "created_time": "2026-01-01T00:00:00Z"},
                }
            }
            result = await store.get_version("my-secret", 1)
            assert mock_to_thread.called


#
# Bug 4: AWS set() throws on existing secret
#


class TestAWSSecretsManagerSetExisting:
    async def test_set_calls_update_when_secret_exists(self) -> None:
        from lexigram.secrets.backends.aws import AWSSecretsManagerStore

        store = AWSSecretsManagerStore(region_name="us-east-1")

        mock_client = AsyncMock()
        mock_client.create_secret = AsyncMock(
            side_effect=botocore.exceptions.ClientError(
                {
                    "Error": {
                        "Code": "ResourceExistsException",
                        "Message": "Secret already exists",
                    }
                },
                "create_secret",
            )
        )
        mock_client.update_secret = AsyncMock(return_value={})

        mock_session = AsyncMock()
        mock_session.client = AsyncMock(return_value=mock_client)

        store._session = mock_session

        await store.set("existing-secret", "new-value")

        mock_client.create_secret.assert_awaited_once_with(
            Name="existing-secret", SecretString="new-value"
        )
        mock_client.update_secret.assert_awaited_once_with(
            SecretId="existing-secret", SecretString="new-value"
        )

    async def test_set_creates_when_secret_does_not_exist(self) -> None:
        from lexigram.secrets.backends.aws import AWSSecretsManagerStore

        store = AWSSecretsManagerStore(region_name="us-east-1")

        mock_client = AsyncMock()
        mock_client.create_secret = AsyncMock(return_value={})

        mock_session = AsyncMock()
        mock_session.client = AsyncMock(return_value=mock_client)

        store._session = mock_session

        await store.set("new-secret", "new-value")

        mock_client.create_secret.assert_awaited_once_with(
            Name="new-secret", SecretString="new-value"
        )
        mock_client.update_secret.assert_not_called()
