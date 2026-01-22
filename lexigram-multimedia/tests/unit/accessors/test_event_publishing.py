from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Ok
from lexigram.contracts.multimedia.types import MediaAsset, TTSRequest
from lexigram.multimedia.accessors import SubsystemAccessor
from lexigram.multimedia.events import MultimediaGenerationEvent


@pytest.mark.asyncio
async def test_generate_publishes_event_when_event_bus_bound() -> None:
    backend = AsyncMock()
    backend.generate.return_value = Ok(
        MediaAsset(mime_type="audio/mpeg", provider="elevenlabs", bytes_data=b"12345")
    )
    event_bus = AsyncMock()
    accessor = SubsystemAccessor(
        backend=backend,
        task_manager=None,
        task_name="tts_generation",
        storage=None,
        path_prefix="multimedia/tts/",
        event_bus=event_bus,
        media_type="tts",
    )

    await accessor.generate(TTSRequest(text="hi"))

    event_bus.publish.assert_awaited_once()
    published = event_bus.publish.await_args.args[0]
    assert isinstance(published, MultimediaGenerationEvent)
    assert published.media_type == "tts"
    assert published.provider == "elevenlabs"
