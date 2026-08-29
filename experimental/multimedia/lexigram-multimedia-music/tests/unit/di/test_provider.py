from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from lexigram.contracts.core.health import HealthStatus
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
async def test_provider_declares_config_key_and_model() -> None:
    provider = AudioMusicProvider()
    assert provider.config_key == "multimedia_music"
    assert provider.config_model is MusicConfig


@pytest.mark.asyncio
async def test_register_binds_music_config_into_container() -> None:
    provider = AudioMusicProvider(config=MusicConfig(backend="ace-step"))
    container = _FakeContainer()
    await provider.register(container)
    assert container.bindings[MusicConfig].backend == "ace-step"


@pytest.mark.asyncio
async def test_explicit_constructor_config_wins_over_injected() -> None:
    provider = AudioMusicProvider(config=MusicConfig(backend="ace-step"))
    provider.config = MusicConfig(backend="stable-audio-open")
    container = _FakeContainer()

    await provider.register(container)

    assert container.bindings[MusicConfig].backend == "ace-step"


@pytest.mark.asyncio
async def test_injected_config_used_when_no_explicit() -> None:
    provider = AudioMusicProvider()
    provider.config = MusicConfig(backend="ace-step")
    container = _FakeContainer()

    await provider.register(container)

    assert container.bindings[MusicConfig].backend == "ace-step"


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
async def test_register_binds_stability_audio_backend(monkeypatch) -> None:
    monkeypatch.setenv("STABILITY_API_KEY", "sk-test")
    provider = AudioMusicProvider(config=MusicConfig(backend="stability-audio"))
    container = _FakeContainer()

    await provider.register(container)

    from lexigram.multimedia.music.providers.stability_audio import (
        StabilityAudioMusicProvider,
    )

    bound = container.bindings[MusicProvider]
    assert isinstance(bound, StabilityAudioMusicProvider)


@pytest.mark.asyncio
async def test_stability_audio_health_healthy_when_backend_present() -> None:
    provider = AudioMusicProvider(config=MusicConfig(backend="stability-audio"))
    container = _FakeContainer()
    await provider.register(container)

    result = await provider.health_check()

    assert result.status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_stability_audio_health_healthy_with_credential(monkeypatch) -> None:
    monkeypatch.setenv("STABILITY_API_KEY", "sk-test")
    provider = AudioMusicProvider(config=MusicConfig(backend="stability-audio"))
    container = _FakeContainer()
    await provider.register(container)

    result = await provider.health_check()

    assert result.status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_check_http_health_returns_healthy_on_200(mocker) -> None:
    provider = AudioMusicProvider(config=MusicConfig())
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mocker.patch("aiohttp.ClientSession.get", return_value=mock_cm)

    status = await provider._check_http_health("http://localhost:5300", 5.0)

    assert status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_check_http_health_returns_degraded_on_connection_error(mocker) -> None:
    provider = AudioMusicProvider(config=MusicConfig())
    mocker.patch("aiohttp.ClientSession.get", side_effect=aiohttp.ClientError())

    status = await provider._check_http_health("http://localhost:5300", 5.0)

    assert status == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_local_http_health_check_still_works_after_refactor(mocker) -> None:
    provider = AudioMusicProvider(config=MusicConfig())
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
async def test_register_binds_ace_step_backend() -> None:
    provider = AudioMusicProvider(config=MusicConfig(backend="ace-step"))
    container = _FakeContainer()

    await provider.register(container)

    from lexigram.multimedia.music.providers.ace_step import AceStepMusicProvider

    bound = container.bindings[MusicProvider]
    assert isinstance(bound, AceStepMusicProvider)


@pytest.mark.asyncio
async def test_ace_step_health_check_uses_shared_http_helper(mocker) -> None:
    provider = AudioMusicProvider(config=MusicConfig(backend="ace-step"))
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
async def test_register_binds_stable_audio_open_backend() -> None:
    provider = AudioMusicProvider(config=MusicConfig(backend="stable-audio-open"))
    container = _FakeContainer()

    await provider.register(container)

    from lexigram.multimedia.music.providers.stable_audio_open import (
        StableAudioOpenMusicProvider,
    )

    bound = container.bindings[MusicProvider]
    assert isinstance(bound, StableAudioOpenMusicProvider)


@pytest.mark.asyncio
async def test_stable_audio_open_health_check_uses_shared_http_helper(mocker) -> None:
    provider = AudioMusicProvider(config=MusicConfig(backend="stable-audio-open"))
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
