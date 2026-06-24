from __future__ import annotations

import pytest

from lexigram.di.container.container import Container
from lexigram.secrets.config import SecretsConfig
from lexigram.secrets.di.provider import SecretsProvider
from lexigram.secrets.module import SecretsModule
from lexigram.secrets.types import RotatableSecretStoreProtocol


@pytest.mark.asyncio
async def test_provider_registers_store() -> None:
    config = SecretsConfig(backend_type="memory")
    provider = SecretsProvider(config=config)
    container = Container()

    await provider.register(container)
    container.freeze()

    store = await container.resolve(RotatableSecretStoreProtocol)
    assert store is not None
    await store.set("key", "val")
    result = await store.get("key")
    assert result == "val"


@pytest.mark.asyncio
async def test_provider_memory_backend_is_real_store_not_test_fake() -> None:
    """The memory backend is the runtime store, never the testing fake."""
    from lexigram.secrets.backends.memory import InMemoryRotatableSecretStore

    config = SecretsConfig(backend_type="memory")
    provider = SecretsProvider(config=config)
    container = Container()

    await provider.register(container)
    container.freeze()

    store = await container.resolve(RotatableSecretStoreProtocol)
    assert isinstance(store, InMemoryRotatableSecretStore)
    assert type(store).__module__ != "lexigram.testing.fakes"


@pytest.mark.asyncio
async def test_provider_boot_creates_decorator() -> None:
    config = SecretsConfig(backend_type="memory")
    provider = SecretsProvider(config=config)
    container = Container()

    await provider.register(container)
    container.freeze()
    await provider.boot(container)

    from lexigram.secrets.rotation import RotationDecorator

    decorator = await container.resolve(RotationDecorator)
    assert decorator is not None


@pytest.mark.asyncio
async def test_provider_disabled_skips_registration() -> None:
    config = SecretsConfig(enabled=False)
    provider = SecretsProvider(config=config)
    container = Container()

    await provider.register(container)
    container.freeze()

    with pytest.raises(Exception):
        await container.resolve(RotatableSecretStoreProtocol)


@pytest.mark.asyncio
async def test_provider_with_tenant() -> None:
    config = SecretsConfig(backend_type="memory", tenant_id="myapp")
    provider = SecretsProvider(config=config)
    container = Container()

    await provider.register(container)
    container.freeze()

    store = await container.resolve(RotatableSecretStoreProtocol)
    await store.set("key", "val")
    assert await store.get("key") == "val"

    from lexigram.secrets.tenancy import TenantScopedSecretStore

    assert isinstance(store, TenantScopedSecretStore)


@pytest.mark.asyncio
async def test_provider_from_config() -> None:
    config = SecretsConfig(backend_type="memory")
    provider = SecretsProvider.from_config(config=config)
    container = Container()
    await provider.register(container)
    container.freeze()
    store = await container.resolve(RotatableSecretStoreProtocol)
    assert store is not None


@pytest.mark.asyncio
async def test_provider_health_check() -> None:
    config = SecretsConfig(backend_type="memory")
    provider = SecretsProvider(config=config)
    result = await provider.health_check()
    assert result.status == "healthy"
    assert result.component == "secrets"


@pytest.mark.asyncio
async def test_module_configure_returns_dynamic_module() -> None:
    config = SecretsConfig(backend_type="memory")
    dynamic = SecretsModule.configure(config=config)
    assert dynamic.module is SecretsModule
    assert len(dynamic.providers) == 1
    assert isinstance(dynamic.providers[0], SecretsProvider)


@pytest.mark.asyncio
async def test_module_stub() -> None:
    dynamic = SecretsModule.stub()
    assert dynamic.module is SecretsModule
    assert len(dynamic.providers) == 1


@pytest.mark.asyncio
async def test_module_configure_default_config() -> None:
    dynamic = SecretsModule.configure()
    assert dynamic.module is SecretsModule
    assert len(dynamic.providers) == 1


@pytest.mark.asyncio
async def test_provider_shutdown() -> None:
    config = SecretsConfig(backend_type="memory")
    provider = SecretsProvider(config=config)
    container = Container()
    await provider.register(container)
    container.freeze()
    await provider.boot(container)
    await provider.shutdown()


@pytest.mark.asyncio
async def test_provider_with_store_override() -> None:
    from lexigram.testing.fakes import FakeRotatableSecretStore

    store = FakeRotatableSecretStore()
    await store.set("pre", "loaded")
    config = SecretsConfig(enabled=True)
    provider = SecretsProvider(config=config, store=store)
    container = Container()
    await provider.register(container)
    container.freeze()
    resolved = await container.resolve(RotatableSecretStoreProtocol)
    result = await resolved.get("pre")
    assert result == "loaded"
