import pytest

from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError
from lexigram.contracts.multimedia.protocols import UpscaleProvider
from lexigram.multimedia.upscale.config import UpscaleConfig
from lexigram.multimedia.upscale.di.provider import UpscaleGenerationProvider
from lexigram.multimedia.upscale.providers.real_esrgan import RealEsrganUpscaleProvider
from lexigram.multimedia.upscale.tasks import UpscaleTask


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
async def test_provider_declares_config_key_and_model() -> None:
    provider = UpscaleGenerationProvider()
    assert provider.config_key == "multimedia_upscale"
    assert provider.config_model is UpscaleConfig


@pytest.mark.asyncio
async def test_register_binds_upscale_config_into_container() -> None:
    provider = UpscaleGenerationProvider(config=UpscaleConfig(backend="hat"))
    container = _FakeContainer()
    await provider.register(container)
    assert container.bindings[UpscaleConfig].backend == "hat"


@pytest.mark.asyncio
async def test_register_binds_real_esrgan_backend_by_default() -> None:
    provider = UpscaleGenerationProvider(config=UpscaleConfig())
    container = _FakeContainer()

    await provider.register(container)

    bound = container.bindings[UpscaleProvider]
    assert isinstance(bound, RealEsrganUpscaleProvider)


@pytest.mark.asyncio
async def test_register_binds_task_handler() -> None:
    provider = UpscaleGenerationProvider(config=UpscaleConfig())
    container = _FakeContainer()

    await provider.register(container)

    bound_task = container.bindings[UpscaleTask]
    assert isinstance(bound_task, UpscaleTask)


@pytest.mark.asyncio
async def test_health_check_reports_healthy_after_register() -> None:
    provider = UpscaleGenerationProvider(config=UpscaleConfig())
    container = _FakeContainer()
    await provider.register(container)

    result = await provider.health_check()

    assert result.component == "upscale"


@pytest.mark.asyncio
async def test_unknown_backend_raises_not_installed() -> None:
    provider = UpscaleGenerationProvider(
        config=UpscaleConfig(backend="unknown")  # type: ignore[arg-type]
    )
    container = _FakeContainer()

    with pytest.raises(ProviderNotInstalledError):
        await provider.register(container)


@pytest.mark.asyncio
async def test_register_binds_hat_backend() -> None:
    provider = UpscaleGenerationProvider(config=UpscaleConfig(backend="hat"))
    container = _FakeContainer()

    await provider.register(container)

    from lexigram.multimedia.upscale.providers.hat import HatUpscaleProvider

    bound = container.bindings[UpscaleProvider]
    assert isinstance(bound, HatUpscaleProvider)


@pytest.mark.asyncio
async def test_hat_health_check(mocker) -> None:
    from unittest.mock import AsyncMock, MagicMock

    provider = UpscaleGenerationProvider(config=UpscaleConfig(backend="hat"))
    container = _FakeContainer()
    await provider.register(container)
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mocker.patch("aiohttp.ClientSession.get", return_value=mock_cm)

    result = await provider.health_check()

    from lexigram.contracts.core.health import HealthStatus

    assert result.status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_register_binds_video_upscale_service_when_video_processor_present() -> (
    None
):
    from unittest.mock import AsyncMock

    from lexigram.contracts.multimedia.protocols import VideoProcessor
    from lexigram.multimedia.upscale.video_upscale_service import VideoUpscaleService

    provider = UpscaleGenerationProvider(config=UpscaleConfig())
    container = _FakeContainer()
    container.singleton(VideoProcessor, AsyncMock())

    await provider.register(container)

    bound = container.bindings[VideoUpscaleService]
    assert isinstance(bound, VideoUpscaleService)


@pytest.mark.asyncio
async def test_video_upscale_service_not_registered_without_video_processor() -> None:
    from lexigram.multimedia.upscale.video_upscale_service import VideoUpscaleService

    provider = UpscaleGenerationProvider(config=UpscaleConfig())
    container = _FakeContainer()

    await provider.register(container)

    assert VideoUpscaleService not in container.bindings
    with pytest.raises(LookupError):
        await container.resolve(VideoUpscaleService)
