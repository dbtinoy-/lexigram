from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.data.vector.protocols import VectorStoreProtocol
from lexigram.di.provider import ProviderState
from lexigram.vector.config import VectorConfig
from lexigram.vector.di.provider import VectorProvider


class _RegistrarStub:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object, dict[str, object]]] = []

    def singleton(self, service_type: object, instance: object = None, **kwargs: object) -> None:
        self.calls.append((service_type, instance, kwargs))


def test_vector_provider_initializes_provider_base_state() -> None:
    provider = VectorProvider()

    assert provider.state == ProviderState.CREATED


@pytest.mark.asyncio
async def test_register_registers_config_and_vector_store_binding() -> None:
    provider = VectorProvider(config=VectorConfig(backend="memory"))
    container = _RegistrarStub()

    await provider.register(container)

    registered_types = [call[0] for call in container.calls]
    assert VectorConfig in registered_types
    assert VectorStoreProtocol in registered_types


@pytest.mark.asyncio
async def test_boot_and_shutdown_manage_store_lifecycle() -> None:
    from unittest.mock import MagicMock, patch

    provider = VectorProvider(config=VectorConfig(backend="memory"))
    mock_store = AsyncMock()
    container = MagicMock()

    with patch("lexigram.vector.backends.memory.MemoryVectorStore", return_value=mock_store):
        await provider.boot(container)

    await provider.shutdown()

    mock_store.connect.assert_awaited_once()
    mock_store.disconnect.assert_awaited_once()
