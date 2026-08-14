from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import BeatAnalysisRequest, MediaAsset
from lexigram.multimedia.beat.providers.madmom import MadmomBeatAnalysisProvider


def _mock_cm(resp: MagicMock) -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_analyze_returns_ok_with_tempo_and_beats() -> None:
    provider = MadmomBeatAnalysisProvider(base_url="http://localhost:5600")
    asset = MediaAsset(mime_type="audio/mpeg", provider="test", bytes_data=b"audio")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(
        return_value={"tempo_bpm": 128.0, "beat_timestamps": [0.0, 0.47, 0.94]}
    )

    with patch("aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)):
        result = await provider.analyze(BeatAnalysisRequest(asset=asset))

    assert result.is_ok()
    analysis = result.unwrap()
    assert analysis.tempo_bpm == 128.0
    assert analysis.beat_timestamps == [0.0, 0.47, 0.94]


@pytest.mark.asyncio
async def test_analyze_returns_err_on_non_200() -> None:
    provider = MadmomBeatAnalysisProvider(base_url="http://localhost:5600")
    asset = MediaAsset(mime_type="audio/mpeg", provider="test", bytes_data=b"audio")

    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="server error")

    with patch("aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)):
        result = await provider.analyze(BeatAnalysisRequest(asset=asset))

    assert result.is_err()


@pytest.mark.asyncio
async def test_analyze_returns_err_on_connection_error() -> None:
    import aiohttp

    provider = MadmomBeatAnalysisProvider(base_url="http://localhost:5600")
    asset = MediaAsset(mime_type="audio/mpeg", provider="test", bytes_data=b"audio")

    with patch("aiohttp.ClientSession.post", side_effect=aiohttp.ClientError()):
        result = await provider.analyze(BeatAnalysisRequest(asset=asset))

    assert result.is_err()
