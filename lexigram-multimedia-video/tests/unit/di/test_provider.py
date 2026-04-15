import pytest

from lexigram.contracts.multimedia.protocols import VideoProcessor, VideoProvider
from lexigram.multimedia.video.config import VideoConfig
from lexigram.multimedia.video.di.provider import VideoGenerationProvider
from lexigram.multimedia.video.providers.local_http import LocalHttpVideoProvider
from lexigram.multimedia.video.tasks import VideoGenerationTask


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
    provider = VideoGenerationProvider(config=VideoConfig())
    container = _FakeContainer()

    await provider.register(container)

    bound = container.bindings[VideoProvider]
    assert isinstance(bound, LocalHttpVideoProvider)


@pytest.mark.asyncio
async def test_health_check_reports_healthy_after_register() -> None:
    provider = VideoGenerationProvider(config=VideoConfig())
    container = _FakeContainer()
    await provider.register(container)

    result = await provider.health_check()

    assert result.component == "video"


@pytest.mark.asyncio
async def test_register_binds_task_handler() -> None:
    provider = VideoGenerationProvider(config=VideoConfig())
    container = _FakeContainer()

    await provider.register(container)

    bound_task = container.bindings[VideoGenerationTask]
    assert isinstance(bound_task, VideoGenerationTask)


@pytest.mark.asyncio
async def test_runway_backend_registers_runway_provider() -> None:
    provider = VideoGenerationProvider(
        config=VideoConfig(backend="runway"),
    )
    container = _FakeContainer()

    await provider.register(container)

    bound = container.bindings[VideoProvider]
    assert bound.__class__.__name__ == "RunwayVideoProvider"


@pytest.mark.asyncio
async def test_unknown_backend_raises_not_installed() -> None:
    from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError

    provider = VideoGenerationProvider(config=VideoConfig(backend="impossible"))
    container = _FakeContainer()

    with pytest.raises(ProviderNotInstalledError):
        await provider.register(container)


@pytest.mark.asyncio
async def test_register_binds_video_processor() -> None:
    provider = VideoGenerationProvider(config=VideoConfig())
    container = _FakeContainer()

    await provider.register(container)

    assert VideoProcessor in container.bindings
    assert provider._processing_backend is not None
    assert provider._processing_task_handler is not None
