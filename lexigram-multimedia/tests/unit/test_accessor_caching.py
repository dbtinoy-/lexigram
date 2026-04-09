from dataclasses import asdict
from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Ok
from lexigram.contracts.multimedia.types import MediaAsset, TTSRequest
from lexigram.multimedia.accessors import SubsystemAccessor


@pytest.mark.asyncio
async def test_generate_checks_cache_before_calling_backend_when_bound() -> None:
    cached_asset = MediaAsset(mime_type="audio/mpeg", provider="cache", bytes_data=b"cached")
    cache = AsyncMock()
    cache.get.return_value = Ok(cached_asset)

    backend = AsyncMock()
    accessor = SubsystemAccessor(
        backend=backend,
        task_manager=None,
        task_name="tts_generation",
        storage=None,
        path_prefix="multimedia/tts/",
        cache_backend=cache,
    )

    result = await accessor.generate(TTSRequest(text="hi"))

    backend.generate.assert_not_awaited()
    assert result.unwrap().provider == "cache"


@pytest.mark.asyncio
async def test_generate_calls_backend_and_writes_cache_on_miss() -> None:
    cache = AsyncMock()
    cache.get.return_value = Ok(None)
    backend = AsyncMock()
    backend.generate.return_value = Ok(
        MediaAsset(mime_type="audio/mpeg", provider="elevenlabs", bytes_data=b"fresh")
    )
    accessor = SubsystemAccessor(
        backend=backend,
        task_manager=None,
        task_name="tts_generation",
        storage=None,
        path_prefix="multimedia/tts/",
        cache_backend=cache,
    )

    result = await accessor.generate(TTSRequest(text="hi"))

    backend.generate.assert_awaited_once()
    cache.set.assert_awaited_once()
    assert result.unwrap().provider == "elevenlabs"
