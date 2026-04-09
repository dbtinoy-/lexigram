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
