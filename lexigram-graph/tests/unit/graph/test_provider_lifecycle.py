from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.data.graph.protocols import GraphStoreProtocol
from lexigram.di.provider import ProviderState
from lexigram.graph.config import GraphConfig
from lexigram.graph.di.provider import GraphProvider


class _RegistrarStub:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object, dict[str, object]]] = []

    def singleton(self, service_type: object, instance: object = None, **kwargs: object) -> None:
        self.calls.append((service_type, instance, kwargs))


class _ResolverStub:
    def __init__(self, store: object) -> None:
        self._store = store

    async def resolve(self, service_type: object) -> object:
        if service_type is GraphStoreProtocol:
            return self._store
        msg = f"Unexpected resolve target: {service_type!r}"
        raise LookupError(msg)

    def bind(self, service_type: type, instance: object) -> None:
        pass


def test_graph_provider_initializes_provider_base_state() -> None:
    provider = GraphProvider()

    assert provider.state == ProviderState.CREATED


@pytest.mark.asyncio
async def test_register_registers_config_and_graph_store_binding() -> None:
    provider = GraphProvider(config=GraphConfig(backend="memory"))
    container = _RegistrarStub()

    await provider.register(container)

    registered_types = [call[0] for call in container.calls]
    assert GraphConfig in registered_types
    assert GraphStoreProtocol in registered_types


@pytest.mark.asyncio
async def test_boot_and_shutdown_manage_store_lifecycle() -> None:
    provider = GraphProvider(config=GraphConfig(backend="memory"))
    store = AsyncMock()
    container = _ResolverStub(store)

    await provider.boot(container)
    await provider.shutdown()

    store.connect.assert_awaited_once()
    store.disconnect.assert_awaited_once()
