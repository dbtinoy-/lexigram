from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import MusicRequest
from lexigram.multimedia.music.providers.stable_audio_open import (
    StableAudioOpenMusicProvider,
)


def _mock_cm(resp: MagicMock) -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_generate_returns_ok_with_bytes() -> None:
    provider = StableAudioOpenMusicProvider(base_url="http://localhost:5301")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"RIFF....audio-bytes")
    mock_resp.headers = {"Content-Type": "audio/wav"}

    with patch("aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)):
        result = await provider.generate(
            MusicRequest(prompt="rain on a tin roof", duration_seconds=10.0)
        )

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.provider == "stable-audio-open"
    assert asset.mime_type == "audio/wav"


@pytest.mark.asyncio
async def test_generate_does_not_send_tags_or_lyrics() -> None:
    provider = StableAudioOpenMusicProvider(base_url="http://localhost:5301")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"audio-bytes")
    mock_resp.headers = {"Content-Type": "audio/wav"}

    with patch(
        "aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)
    ) as mock_post:
        await provider.generate(MusicRequest(prompt="a passing train"))

    sent_payload = mock_post.call_args.kwargs["json"]
    assert "tags" not in sent_payload
    assert "lyrics" not in sent_payload


@pytest.mark.asyncio
async def test_generate_returns_err_on_non_200() -> None:
    provider = StableAudioOpenMusicProvider(base_url="http://localhost:5301")

    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="server error")

    with patch("aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)):
        result = await provider.generate(MusicRequest(prompt="a passing train"))

    assert result.is_err()


@pytest.mark.asyncio
async def test_generate_returns_err_on_connection_error() -> None:
    provider = StableAudioOpenMusicProvider(base_url="http://localhost:5301")

    import aiohttp

    with patch("aiohttp.ClientSession.post", side_effect=aiohttp.ClientError()):
        result = await provider.generate(MusicRequest(prompt="a passing train"))

    assert result.is_err()
