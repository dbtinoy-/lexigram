"""Focused tests for the audit bundle provider composition."""

from __future__ import annotations

import pytest

from lexigram.audit.config import AuditConfig
from lexigram.audit.di.bundle_provider import AuditBundleProvider
from lexigram.di.container.container import Container


@pytest.mark.asyncio
async def test_bundle_provider_register_and_boot() -> None:
    config = AuditConfig(store_backend="memory")
    provider = AuditBundleProvider(config=config)
    container = Container()
    await provider.register(container)
    container.freeze()
    await provider.boot(container)
    await provider.shutdown()


@pytest.mark.asyncio
async def test_bundle_provider_admin_disabled() -> None:
    provider = AuditBundleProvider(config=AuditConfig(store_backend="memory"), enable_admin=False)
    container = Container()
    await provider.register(container)
    container.freeze()
    await provider.boot(container)
    await provider.shutdown()


def test_bundle_provider_defaults() -> None:
    provider = AuditBundleProvider()
    assert provider.name == "audit_bundle"


def test_bundle_provider_config_attrs() -> None:
    assert AuditBundleProvider.config_key == "audit"
    assert AuditBundleProvider.config_model is AuditConfig