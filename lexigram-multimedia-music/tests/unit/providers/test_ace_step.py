from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import MusicRequest
from lexigram.multimedia.music.providers.ace_step import AceStepMusicProvider


def _mock_cm(resp: MagicMock) -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_generate_returns_ok_with_bytes() -> None:
    provider = AceStepMusicProvider(base_url="http://localhost:5300")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"RIFF....audio-bytes")
    mock_resp.headers = {"Content-Type": "audio/wav"}

    with patch("aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)):
        result = await provider.generate(
            MusicRequest(prompt="an upbeat synthwave track")
        )

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.provider == "ace-step"
    assert asset.mime_type == "audio/wav"


@pytest.mark.asyncio
async def test_generate_sends_tags_and_lyrics_when_present() -> None:
    provider = AceStepMusicProvider(base_url="http://localhost:5300")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"audio-bytes")
    mock_resp.headers = {"Content-Type": "audio/wav"}

    with patch(
        "aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)
    ) as mock_post:
        await provider.generate(
            MusicRequest(
                prompt="a power ballad",
                extra={"tags": "rock, power ballad", "lyrics": "we will rise again"},
            )
        )

    sent_payload = mock_post.call_args.kwargs["json"]
    assert sent_payload["tags"] == "rock, power ballad"
    assert sent_payload["lyrics"] == "we will rise again"


@pytest.mark.asyncio
async def test_generate_defaults_tags_and_lyrics_to_empty_when_extra_omitted() -> None:
    provider = AceStepMusicProvider(base_url="http://localhost:5300")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"audio-bytes")
    mock_resp.headers = {"Content-Type": "audio/wav"}

    with patch(
        "aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)
    ) as mock_post:
        result = await provider.generate(MusicRequest(prompt="lo-fi beats"))

    assert result.is_ok()
    sent_payload = mock_post.call_args.kwargs["json"]
    assert sent_payload["tags"] == ""
    assert sent_payload["lyrics"] == ""


@pytest.mark.asyncio
async def test_generate_returns_err_on_non_200() -> None:
    provider = AceStepMusicProvider(base_url="http://localhost:5300")

    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="server error")

    with patch("aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)):
        result = await provider.generate(MusicRequest(prompt="lo-fi beats"))

    assert result.is_err()


@pytest.mark.asyncio
async def test_generate_returns_err_on_connection_error() -> None:
    provider = AceStepMusicProvider(base_url="http://localhost:5300")

    import aiohttp

    with patch("aiohttp.ClientSession.post", side_effect=aiohttp.ClientError()):
        result = await provider.generate(MusicRequest(prompt="lo-fi beats"))

    assert result.is_err()
