from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import TTSRequest
from lexigram.multimedia.tts.providers.piper import PiperTTSProvider


@pytest.mark.asyncio
async def test_generate_returns_ok_with_wav_bytes() -> None:
    provider = PiperTTSProvider(base_url="http://localhost:5103")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"RIFF....wav-bytes")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(TTSRequest(text="hello world"))

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.mime_type == "audio/wav"
    assert asset.provider == "piper"


@pytest.mark.asyncio
async def test_generate_falls_back_to_default_voice() -> None:
    provider = PiperTTSProvider(
        base_url="http://localhost:5103", default_voice="en_US-lessac-medium"
    )

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"wav")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm) as mock_post:
        await provider.generate(TTSRequest(text="hello", voice=None))

    assert mock_post.call_args.kwargs["json"]["voice"] == "en_US-lessac-medium"


@pytest.mark.asyncio
async def test_generate_returns_err_on_non_200() -> None:
    provider = PiperTTSProvider(base_url="http://localhost:5103")

    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="server error")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(TTSRequest(text="hello"))

    assert result.is_err()
