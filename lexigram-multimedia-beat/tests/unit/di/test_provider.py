from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError
from lexigram.contracts.multimedia.protocols import BeatAnalysisProvider
from lexigram.multimedia.beat.config import BeatAnalysisConfig
from lexigram.multimedia.beat.di.provider import BeatAnalysisGenerationProvider
from lexigram.multimedia.beat.providers.librosa import LibrosaBeatAnalysisProvider
from lexigram.multimedia.beat.providers.madmom import MadmomBeatAnalysisProvider


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
async def test_register_binds_librosa_backend_by_default() -> None:
    provider = BeatAnalysisGenerationProvider(config=BeatAnalysisConfig())
    container = _FakeContainer()

    await provider.register(container)

    bound = container.bindings[BeatAnalysisProvider]
    assert isinstance(bound, LibrosaBeatAnalysisProvider)


@pytest.mark.asyncio
async def test_register_binds_madmom_backend_when_configured() -> None:
    provider = BeatAnalysisGenerationProvider(
        config=BeatAnalysisConfig(backend="madmom")
    )
    container = _FakeContainer()

    await provider.register(container)

    bound = container.bindings[BeatAnalysisProvider]
    assert isinstance(bound, MadmomBeatAnalysisProvider)


@pytest.mark.asyncio
async def test_librosa_health_check_reports_healthy_with_no_network_call() -> None:
    provider = BeatAnalysisGenerationProvider(config=BeatAnalysisConfig())
    container = _FakeContainer()
    await provider.register(container)

    with patch("aiohttp.ClientSession.get") as mock_get:
        result = await provider.health_check()

    mock_get.assert_not_called()
    assert result.component == "beat"


@pytest.mark.asyncio
async def test_madmom_health_check_makes_network_call() -> None:
    provider = BeatAnalysisGenerationProvider(
        config=BeatAnalysisConfig(backend="madmom")
    )
    container = _FakeContainer()
    await provider.register(container)

    mock_resp = MagicMock()
    mock_resp.status = 200
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_resp)
    cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.get", return_value=cm) as mock_get:
        await provider.health_check()

    mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_unknown_backend_raises_not_installed() -> None:
    provider = BeatAnalysisGenerationProvider(
        config=BeatAnalysisConfig(backend="unknown")  # type: ignore[arg-type]
    )
    container = _FakeContainer()

    with pytest.raises(ProviderNotInstalledError):
        await provider.register(container)
