import pytest

from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError
from lexigram.contracts.multimedia.protocols import InterpolationProvider
from lexigram.multimedia.interpolate.config import InterpolationConfig
from lexigram.multimedia.interpolate.di.provider import InterpolationGenerationProvider
from lexigram.multimedia.interpolate.providers.rife import RifeInterpolationProvider


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
async def test_register_binds_rife_backend_by_default() -> None:
    provider = InterpolationGenerationProvider(config=InterpolationConfig())
    container = _FakeContainer()

    await provider.register(container)

    bound = container.bindings[InterpolationProvider]
    assert isinstance(bound, RifeInterpolationProvider)


@pytest.mark.asyncio
async def test_health_check_reports_healthy_after_register() -> None:
    provider = InterpolationGenerationProvider(config=InterpolationConfig())
    container = _FakeContainer()
    await provider.register(container)

    result = await provider.health_check()

    assert result.component == "interpolate"


@pytest.mark.asyncio
async def test_unknown_backend_raises_not_installed() -> None:
    provider = InterpolationGenerationProvider(
        config=InterpolationConfig(backend="unknown")  # type: ignore[arg-type]
    )
    container = _FakeContainer()

    with pytest.raises(ProviderNotInstalledError):
        await provider.register(container)


@pytest.mark.asyncio
async def test_register_binds_video_interpolation_service_when_video_processor_present() -> (
    None
):
    from unittest.mock import AsyncMock

    from lexigram.contracts.multimedia.protocols import VideoProcessor
    from lexigram.multimedia.interpolate.video_interpolation_service import (
        VideoInterpolationService,
    )

    provider = InterpolationGenerationProvider(config=InterpolationConfig())
    container = _FakeContainer()
    container.singleton(VideoProcessor, AsyncMock())

    await provider.register(container)

    bound = container.bindings[VideoInterpolationService]
    assert isinstance(bound, VideoInterpolationService)


@pytest.mark.asyncio
async def test_video_interpolation_service_not_registered_without_video_processor() -> (
    None
):
    from lexigram.multimedia.interpolate.video_interpolation_service import (
        VideoInterpolationService,
    )

    provider = InterpolationGenerationProvider(config=InterpolationConfig())
    container = _FakeContainer()

    await provider.register(container)

    assert VideoInterpolationService not in container.bindings
    with pytest.raises(LookupError):
        await container.resolve(VideoInterpolationService)
