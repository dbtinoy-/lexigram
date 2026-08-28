import shutil
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from lexigram.contracts.core.health import HealthStatus
from lexigram.contracts.multimedia.protocols import VideoProcessor, VideoProvider
from lexigram.multimedia.video.config import VideoConfig
from lexigram.multimedia.video.di.provider import VideoGenerationProvider
from lexigram.multimedia.video.providers.local_http import LocalHttpVideoProvider
from lexigram.multimedia.video.tasks import VideoGenerationTask, VideoProcessingTask


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
async def test_openai_backend_registers_without_ffmpeg(monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _cmd: None)

    provider = VideoGenerationProvider(
        config=VideoConfig(backend="openai", openai_api_key_secret_name="lex_openai")
    )
    container = _FakeContainer()
    await provider.register(container)

    assert container.bindings[VideoProvider] is not None
    assert VideoProcessingTask not in container.bindings


@pytest.mark.asyncio
async def test_local_http_backend_registers_without_ffmpeg(monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _cmd: None)

    provider = VideoGenerationProvider(config=VideoConfig(backend="local-http"))
    container = _FakeContainer()
    await provider.register(container)

    assert container.bindings[VideoProvider] is not None


@pytest.mark.asyncio
async def test_processing_pipeline_registered_when_ffmpeg_present(mocker) -> None:
    mocker.patch("shutil.which", return_value="/usr/bin/ffmpeg")

    provider = VideoGenerationProvider(config=VideoConfig(backend="local-http"))
    container = _FakeContainer()
    await provider.register(container)

    assert container.bindings[VideoProcessingTask] is not None


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
async def test_register_binds_video_processor(mocker) -> None:
    # Deterministic: assert the enabled path regardless of whether the
    # runner image ships ffmpeg.  (test_local_http_backend_registers_without_ffmpeg
    # covers the disabled path.)
    mocker.patch("shutil.which", return_value="/usr/bin/ffmpeg")

    provider = VideoGenerationProvider(config=VideoConfig())
    container = _FakeContainer()

    await provider.register(container)

    assert VideoProcessor in container.bindings
    assert provider._processing_backend is not None
    assert provider._processing_task_handler is not None


@pytest.mark.asyncio
async def test_check_http_health_returns_healthy_on_200(mocker) -> None:
    provider = VideoGenerationProvider(config=VideoConfig())
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mocker.patch("aiohttp.ClientSession.get", return_value=mock_cm)

    status = await provider._check_http_health("http://localhost:5200", 5.0)

    assert status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_check_http_health_returns_degraded_on_connection_error(mocker) -> None:
    provider = VideoGenerationProvider(config=VideoConfig())
    mocker.patch("aiohttp.ClientSession.get", side_effect=aiohttp.ClientError())

    status = await provider._check_http_health("http://localhost:5200", 5.0)

    assert status == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_check_http_health_uses_system_stats_for_comfyui(mocker) -> None:
    provider = VideoGenerationProvider(config=VideoConfig())
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_get = mocker.patch("aiohttp.ClientSession.get", return_value=mock_cm)

    await provider._check_http_health(provider._config.comfyui_base_url, 5.0)

    called_url = mock_get.call_args.args[0]
    assert called_url == f"{provider._config.comfyui_base_url}/system_stats"


@pytest.mark.asyncio
async def test_runway_health_check_degraded_without_resolved_credential(
    monkeypatch,
) -> None:
    monkeypatch.delenv("RUNWAY_API_KEY", raising=False)
    provider = VideoGenerationProvider(config=VideoConfig(backend="runway"))
    container = _FakeContainer()
    await provider.register(container)

    result = await provider.health_check()

    assert result.status == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_runway_health_check_healthy_with_resolved_credential(
    monkeypatch,
) -> None:
    monkeypatch.setenv("RUNWAY_API_KEY", "test-key")
    provider = VideoGenerationProvider(config=VideoConfig(backend="runway"))
    container = _FakeContainer()
    await provider.register(container)

    result = await provider.health_check()

    assert result.status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_register_binds_openai_backend(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    provider = VideoGenerationProvider(config=VideoConfig(backend="openai"))
    container = _FakeContainer()

    await provider.register(container)

    from lexigram.multimedia.video.providers.openai import OpenAIVideoProvider

    bound = container.bindings[VideoProvider]
    assert isinstance(bound, OpenAIVideoProvider)


@pytest.mark.asyncio
async def test_openai_health_check_degraded_without_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = VideoGenerationProvider(config=VideoConfig(backend="openai"))
    container = _FakeContainer()
    await provider.register(container)

    result = await provider.health_check()

    assert result.status == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_openai_health_check_healthy_with_key(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    provider = VideoGenerationProvider(config=VideoConfig(backend="openai"))
    container = _FakeContainer()
    await provider.register(container)

    result = await provider.health_check()

    assert result.status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_register_binds_wan22_backend() -> None:
    provider = VideoGenerationProvider(config=VideoConfig(backend="wan22"))
    container = _FakeContainer()

    await provider.register(container)

    from lexigram.multimedia.video.providers.wan22 import Wan22VideoProvider

    bound = container.bindings[VideoProvider]
    assert isinstance(bound, Wan22VideoProvider)


@pytest.mark.asyncio
async def test_wan22_health_check_uses_shared_http_helper(mocker) -> None:
    provider = VideoGenerationProvider(config=VideoConfig(backend="wan22"))
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
async def test_register_binds_cogvideox_backend() -> None:
    provider = VideoGenerationProvider(config=VideoConfig(backend="cogvideox"))
    container = _FakeContainer()

    await provider.register(container)

    from lexigram.multimedia.video.providers.cogvideox import CogVideoXVideoProvider

    bound = container.bindings[VideoProvider]
    assert isinstance(bound, CogVideoXVideoProvider)


@pytest.mark.asyncio
async def test_register_binds_svd_backend() -> None:
    provider = VideoGenerationProvider(config=VideoConfig(backend="svd"))
    container = _FakeContainer()

    await provider.register(container)

    from lexigram.multimedia.video.providers.svd import SVDVideoProvider

    bound = container.bindings[VideoProvider]
    assert isinstance(bound, SVDVideoProvider)


@pytest.mark.asyncio
async def test_register_binds_comfyui_backend() -> None:
    provider = VideoGenerationProvider(config=VideoConfig(backend="comfyui"))
    container = _FakeContainer()

    await provider.register(container)

    from lexigram.multimedia.video.providers.comfyui import ComfyUiVideoProvider

    bound = container.bindings[VideoProvider]
    assert isinstance(bound, ComfyUiVideoProvider)


@pytest.mark.asyncio
async def test_comfyui_health_check_hits_system_stats(mocker) -> None:
    provider = VideoGenerationProvider(config=VideoConfig(backend="comfyui"))
    container = _FakeContainer()
    await provider.register(container)
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_get = mocker.patch("aiohttp.ClientSession.get", return_value=mock_cm)

    result = await provider.health_check()

    assert result.status == HealthStatus.HEALTHY
    called_url = mock_get.call_args.args[0]
    assert called_url.endswith("/system_stats")


@pytest.mark.asyncio
async def test_wan22_backend_gets_its_own_default_timeout_when_unset() -> None:
    provider = VideoGenerationProvider(config=VideoConfig(backend="wan22"))
    container = _FakeContainer()
    await provider.register(container)

    assert provider._backend._timeout == 180.0


@pytest.mark.asyncio
async def test_explicit_timeout_still_overrides_backend_default() -> None:
    provider = VideoGenerationProvider(
        config=VideoConfig(backend="wan22", timeout=30.0)
    )
    container = _FakeContainer()
    await provider.register(container)

    assert provider._backend._timeout == 30.0
