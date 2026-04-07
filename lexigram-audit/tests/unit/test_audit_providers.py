"""Tests for audit DI providers."""

from __future__ import annotations

import pytest

from lexigram.audit.config import AuditConfig
from lexigram.audit.di.sub_providers.admin_provider import AuditAdminProvider
from lexigram.audit.di.sub_providers.core_provider import AuditCoreProvider
from lexigram.audit.di.sub_providers.retention_provider import AuditRetentionProvider
from lexigram.audit.di.sub_providers.scheduling_provider import (
    AuditSchedulingProvider,
)
from lexigram.audit.di.sub_providers.verifier_provider import AuditVerifierProvider
from lexigram.audit.retention.policy import PolicyBasedRetention
from lexigram.contracts.audit import (
    AuditLoggerProtocol,
    AuditStoreProtocol,
    RetentionPolicyProtocol,
)
from lexigram.di.container import Container


class TestAuditCoreProvider:
    """Tests for AuditCoreProvider."""

    @pytest.mark.asyncio
    async def test_register_binds_store(self) -> None:
        """register() should bind AuditStoreProtocol."""
        provider = AuditCoreProvider(config=AuditConfig(store_backend="memory"))
        container = Container()

        await provider.register(container)
        await provider.boot(container)

        store = await container.resolve(AuditStoreProtocol)
        assert store is not None

    @pytest.mark.asyncio
    async def test_register_binds_config_singleton(self) -> None:
        """register() should register AuditConfig as singleton."""
        provider = AuditCoreProvider(config=AuditConfig(store_backend="memory"))
        container = Container()

        await provider.register(container)

        config = await container.resolve(AuditConfig)
        assert config.store_backend == "memory"

    @pytest.mark.asyncio
    async def test_boot_no_op_when_no_initialize(self) -> None:
        """boot() should handle store without initialize method."""
        provider = AuditCoreProvider(config=AuditConfig(store_backend="memory"))
        container = Container()

        await provider.register(container)
        await provider.boot(container)


class TestAuditRetentionProvider:
    """Tests for AuditRetentionProvider."""

    @pytest.mark.asyncio
    async def test_register_binds_retention_policy(self) -> None:
        """register() should bind RetentionPolicyProtocol."""
        provider = AuditRetentionProvider(
            config=AuditConfig(retention_policy={"max_days": 30})
        )
        container = Container()

        await provider.register(container)
        await provider.boot(container)

        policy = await container.resolve(RetentionPolicyProtocol)
        assert isinstance(policy, PolicyBasedRetention)

    @pytest.mark.asyncio
    async def test_boot_no_op(self) -> None:
        """boot() should be a no-op."""
        provider = AuditRetentionProvider(config=AuditConfig())
        container = Container()

        await provider.register(container)
        await provider.boot(container)


class TestAuditVerifierProvider:
    """Tests for AuditVerifierProvider."""

    @pytest.mark.asyncio
    async def test_no_verifier_when_hmac_not_set(self) -> None:
        """register() should not bind verifier when hmac_key is not set."""
        provider = AuditVerifierProvider(config=AuditConfig())
        container = Container()

        await provider.register(container)
        await provider.boot(container)

        from lexigram.contracts.audit import AuditVerifierProtocol

        verifier = await container.resolve_optional(AuditVerifierProtocol)
        assert verifier is None

    @pytest.mark.asyncio
    async def test_boot_no_op(self) -> None:
        """boot() should be a no-op."""
        provider = AuditVerifierProvider(config=AuditConfig())
        container = Container()

        await provider.register(container)
        await provider.boot(container)


class TestAuditSchedulingProvider:
    """Tests for AuditSchedulingProvider."""

    @pytest.mark.asyncio
    async def test_register_includes_scheduler_binding(self) -> None:
        """register() should attempt to bind scheduler (may fail due to deps)."""
        provider = AuditSchedulingProvider(config=AuditConfig())
        container = Container()

        await provider.register(container)
        await provider.boot(container)

    @pytest.mark.asyncio
    async def test_boot_no_op(self) -> None:
        """boot() should be a no-op."""
        provider = AuditSchedulingProvider(config=AuditConfig())
        container = Container()

        await provider.register(container)
        await provider.boot(container)


class TestAuditAdminProvider:
    """Tests for AuditAdminProvider."""

    @pytest.mark.asyncio
    async def test_register_binds_admin_contributor(self) -> None:
        """register() should bind AuditAdminContributor."""
        provider = AuditAdminProvider(config=AuditConfig())
        container = Container()

        await provider.register(container)
        await provider.boot(container)

        from lexigram.audit.admin.contributor import AuditAdminContributor

        contributor = await container.resolve(AuditAdminContributor)
        assert contributor is not None

    @pytest.mark.asyncio
    async def test_boot_no_op(self) -> None:
        """boot() should be a no-op."""
        provider = AuditAdminProvider(config=AuditConfig())
        container = Container()

        await provider.register(container)
        await provider.boot(container)