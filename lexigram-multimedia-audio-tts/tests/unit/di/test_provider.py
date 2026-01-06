import pytest

from lexigram.contracts.multimedia.protocols import TTSProvider
from lexigram.multimedia.audio_tts.config import TTSConfig
from lexigram.multimedia.audio_tts.di.provider import AudioTTSProvider
from lexigram.multimedia.audio_tts.providers.local_http import LocalHttpTTSProvider
from lexigram.multimedia.audio_tts.tasks import TTSGenerationTask


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
async def test_register_binds_local_http_backend_by_default() -> None:
    provider = AudioTTSProvider(config=TTSConfig())
    container = _FakeContainer()

    await provider.register(container)

    bound = container.bindings[TTSProvider]
    assert isinstance(bound, LocalHttpTTSProvider)


@pytest.mark.asyncio
async def test_health_check_reports_healthy_after_register() -> None:
    provider = AudioTTSProvider(config=TTSConfig())
    container = _FakeContainer()
    await provider.register(container)

    result = await provider.health_check()

    assert result.component == "audio-tts"


@pytest.mark.asyncio
async def test_register_binds_task_handler() -> None:
    provider = AudioTTSProvider(config=TTSConfig())
    container = _FakeContainer()

    await provider.register(container)

    bound_task = container.bindings[TTSGenerationTask]
    assert isinstance(bound_task, TTSGenerationTask)
