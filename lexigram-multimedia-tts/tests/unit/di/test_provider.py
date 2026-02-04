import aiohttp
import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.contracts.core.health import HealthStatus
from lexigram.contracts.multimedia.protocols import TTSProvider
from lexigram.multimedia.tts.config import TTSConfig
from lexigram.multimedia.tts.di.provider import AudioTTSProvider
from lexigram.multimedia.tts.providers.local_http import LocalHttpTTSProvider
from lexigram.multimedia.tts.tasks import TTSGenerationTask


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

    assert result.component == "tts"


@pytest.mark.asyncio
async def test_register_binds_task_handler() -> None:
    provider = AudioTTSProvider(config=TTSConfig())
    container = _FakeContainer()

    await provider.register(container)

    bound_task = container.bindings[TTSGenerationTask]
    assert isinstance(bound_task, TTSGenerationTask)


@pytest.mark.asyncio
async def test_check_http_health_returns_healthy_on_200(mocker) -> None:
    provider = AudioTTSProvider(config=TTSConfig())
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mocker.patch("aiohttp.ClientSession.get", return_value=mock_cm)

    status = await provider._check_http_health("http://localhost:5100", 5.0)

    assert status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_check_http_health_returns_degraded_on_connection_error(mocker) -> None:
    provider = AudioTTSProvider(config=TTSConfig())
    mocker.patch("aiohttp.ClientSession.get", side_effect=aiohttp.ClientError())

    status = await provider._check_http_health("http://localhost:5100", 5.0)

    assert status == HealthStatus.DEGRADED
