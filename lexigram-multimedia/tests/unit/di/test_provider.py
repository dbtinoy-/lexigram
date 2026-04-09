import pytest

from lexigram.contracts.multimedia.protocols import (
    ImageProvider,
    MusicProvider,
    TTSProvider,
    VideoProvider,
)
from lexigram.multimedia.config import MultimediaConfig
from lexigram.multimedia.di.provider import MultimediaProvider


class _FakeContainer:
    def __init__(self) -> None:
        self.bindings: dict[object, object] = {}

    def singleton(self, key: object, value: object) -> None:
        self.bindings[key] = value

    async def resolve(self, key: object) -> object:
        if key not in self.bindings:
            raise LookupError(key)
        return self.bindings[key]


@pytest.mark.asyncio
async def test_register_hardcodes_all_four_siblings() -> None:
    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()

    await provider.register(container)

    for protocol in (TTSProvider, MusicProvider, VideoProvider, ImageProvider):
        assert protocol in container.bindings


@pytest.mark.asyncio
async def test_tts_accessor_generate_delegates_to_backend() -> None:
    from unittest.mock import AsyncMock

    from lexigram.contracts.core.result import Ok
    from lexigram.contracts.multimedia.types import MediaAsset, TTSRequest

    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()
    await provider.register(container)

    fake_backend = AsyncMock()
    fake_backend.generate.return_value = Ok(
        MediaAsset(mime_type="audio/mpeg", provider="local-http", bytes_data=b"x")
    )
    provider._sub_providers["audio-tts"]._backend = fake_backend

    accessor = provider.tts
    result = await accessor.generate(TTSRequest(text="hi"))

    assert result.is_ok()
    fake_backend.generate.assert_awaited_once()
