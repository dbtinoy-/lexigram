import pytest

from lexigram.contracts.multimedia.protocols import MusicProvider
from lexigram.multimedia.music.config import MusicConfig
from lexigram.multimedia.music.di.provider import AudioMusicProvider
from lexigram.multimedia.music.providers.local_http import LocalHttpMusicProvider
from lexigram.multimedia.music.tasks import MusicGenerationTask


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
    provider = AudioMusicProvider(config=MusicConfig())
    container = _FakeContainer()

    await provider.register(container)

    bound = container.bindings[MusicProvider]
    assert isinstance(bound, LocalHttpMusicProvider)


@pytest.mark.asyncio
async def test_health_check_reports_healthy_after_register() -> None:
    provider = AudioMusicProvider(config=MusicConfig())
    container = _FakeContainer()
    await provider.register(container)

    result = await provider.health_check()

    assert result.component == "music"


@pytest.mark.asyncio
async def test_register_binds_task_handler() -> None:
    provider = AudioMusicProvider(config=MusicConfig())
    container = _FakeContainer()

    await provider.register(container)

    bound_task = container.bindings[MusicGenerationTask]
    assert isinstance(bound_task, MusicGenerationTask)


@pytest.mark.asyncio
async def test_stability_backend_raises_not_installed() -> None:
    import pytest

    from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError

    provider = AudioMusicProvider(config=MusicConfig(backend="stability-audio"))
    container = _FakeContainer()

    with pytest.raises(ProviderNotInstalledError):
        await provider.register(container)
