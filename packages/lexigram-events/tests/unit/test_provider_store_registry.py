import pytest

from lexigram.events.config import EventsConfig
from lexigram.events.di import EventsProvider
from lexigram.events.types import EventStoreBackend
from lexigram.events.stores import InMemoryEventStore


@pytest.mark.asyncio
async def test_provider_creates_inmemory_store_by_default():
    provider = EventsProvider(
        config=EventsConfig(event_store_backend=EventStoreBackend.MEMORY)
    )
    await provider._create_stores()

    assert isinstance(provider.event_store, InMemoryEventStore)


@pytest.mark.asyncio
async def test_provider_raises_for_missing_mongodb_config():
    cfg = EventsConfig(event_store_backend=EventStoreBackend.MONGODB)
    provider = EventsProvider(config=cfg)

    with pytest.raises(ValueError):
        await provider._create_stores()
