from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import TTSRequest
from lexigram.multimedia.tts.providers.kokoro import KokoroTTSProvider


@pytest.mark.asyncio
async def test_generate_returns_ok_with_wav_bytes() -> None:
    provider = KokoroTTSProvider(base_url="http://localhost:5101")

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
    assert asset.provider == "kokoro"


@pytest.mark.asyncio
async def test_generate_falls_back_to_default_voice() -> None:
    provider = KokoroTTSProvider(
        base_url="http://localhost:5101", default_voice="af_bella"
    )

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"wav")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm) as mock_post:
        await provider.generate(TTSRequest(text="hello", voice=None))

    assert mock_post.call_args.kwargs["json"]["voice"] == "af_bella"


@pytest.mark.asyncio
async def test_generate_uses_request_voice_when_set() -> None:
    provider = KokoroTTSProvider(
        base_url="http://localhost:5101", default_voice="af_bella"
    )

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"wav")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm) as mock_post:
        await provider.generate(TTSRequest(text="hello", voice="af_heart"))

    assert mock_post.call_args.kwargs["json"]["voice"] == "af_heart"


@pytest.mark.asyncio
async def test_generate_returns_err_on_non_200() -> None:
    provider = KokoroTTSProvider(base_url="http://localhost:5101")

    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="server error")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(TTSRequest(text="hello"))

    assert result.is_err()
