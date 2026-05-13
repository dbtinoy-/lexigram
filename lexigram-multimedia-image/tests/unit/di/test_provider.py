from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.core.health import HealthStatus
from lexigram.contracts.multimedia.protocols import ImageProvider
from lexigram.multimedia.image.config import ImageConfig
from lexigram.multimedia.image.di.provider import ImageGenerationProvider
from lexigram.multimedia.image.providers.local_http import LocalHttpImageProvider
from lexigram.multimedia.image.tasks import ImageGenerationTask


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
    provider = ImageGenerationProvider()
    assert provider.config_key == "multimedia_image"
    assert provider.config_model is ImageConfig


@pytest.mark.asyncio
async def test_register_binds_image_config_into_container() -> None:
    provider = ImageGenerationProvider(config=ImageConfig(backend="openai"))
    container = _FakeContainer()
    await provider.register(container)
    assert container.bindings[ImageConfig].backend == "openai"


@pytest.mark.asyncio
async def test_register_binds_local_http_backend_by_default() -> None:
    provider = ImageGenerationProvider(config=ImageConfig())
    container = _FakeContainer()

    await provider.register(container)

    bound = container.bindings[ImageProvider]
    assert isinstance(bound, LocalHttpImageProvider)


@pytest.mark.asyncio
async def test_health_check_reports_healthy_after_register() -> None:
    provider = ImageGenerationProvider(config=ImageConfig())
    container = _FakeContainer()
    await provider.register(container)

    result = await provider.health_check()

    assert result.component == "image"


@pytest.mark.asyncio
async def test_register_binds_task_handler() -> None:
    provider = ImageGenerationProvider(config=ImageConfig())
    container = _FakeContainer()

    await provider.register(container)

    bound_task = container.bindings[ImageGenerationTask]
    assert isinstance(bound_task, ImageGenerationTask)


@pytest.mark.asyncio
async def test_stability_backend_registers_stability_provider() -> None:
    provider = ImageGenerationProvider(
        config=ImageConfig(backend="stability"),
    )
    container = _FakeContainer()

    await provider.register(container)

    bound = container.bindings[ImageProvider]
    assert bound.__class__.__name__ == "StabilityImageProvider"


@pytest.mark.asyncio
async def test_unknown_backend_raises_not_installed() -> None:
    from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError

    provider = ImageGenerationProvider(config=ImageConfig(backend="impossible"))
    container = _FakeContainer()

    with pytest.raises(ProviderNotInstalledError):
        await provider.register(container)


@pytest.mark.asyncio
async def test_register_binds_openai_backend(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    provider = ImageGenerationProvider(config=ImageConfig(backend="openai"))
    container = _FakeContainer()

    await provider.register(container)

    bound = container.bindings[ImageProvider]
    assert bound.__class__.__name__ == "OpenAIImageProvider"


@pytest.mark.asyncio
async def test_openai_health_check_degraded_without_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = ImageGenerationProvider(config=ImageConfig(backend="openai"))
    container = _FakeContainer()
    await provider.register(container)

    result = await provider.health_check()

    assert result.status == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_register_binds_comfyui_backend() -> None:
    provider = ImageGenerationProvider(config=ImageConfig(backend="comfyui"))
    container = _FakeContainer()

    await provider.register(container)

    bound = container.bindings[ImageProvider]
    assert bound.__class__.__name__ == "ComfyUiImageProvider"


@pytest.mark.asyncio
async def test_comfyui_health_check_uses_system_stats_endpoint(mocker) -> None:
    provider = ImageGenerationProvider(config=ImageConfig(backend="comfyui"))
    container = _FakeContainer()
    await provider.register(container)
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mocker.patch("aiohttp.ClientSession.get", return_value=mock_cm)

    result = await provider.health_check()

    assert result.status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_stability_health_check_degraded_without_resolved_credential(
    monkeypatch,
) -> None:
    monkeypatch.delenv("STABILITY_API_KEY", raising=False)
    provider = ImageGenerationProvider(config=ImageConfig(backend="stability"))
    container = _FakeContainer()
    await provider.register(container)

    result = await provider.health_check()

    assert result.status == HealthStatus.DEGRADED
