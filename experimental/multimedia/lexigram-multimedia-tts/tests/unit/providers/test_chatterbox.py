from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import TTSRequest
from lexigram.multimedia.tts.providers.chatterbox import ChatterboxTTSProvider


@pytest.mark.asyncio
async def test_generate_returns_ok_with_wav_bytes() -> None:
    provider = ChatterboxTTSProvider(base_url="http://localhost:5100")

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
    assert asset.has_bytes
    assert asset.mime_type == "audio/wav"
    assert asset.provider == "chatterbox"


@pytest.mark.asyncio
async def test_generate_sends_tuning_params() -> None:
    provider = ChatterboxTTSProvider(
        base_url="http://localhost:5100",
        exaggeration=0.7,
        cfg_weight=0.3,
        temperature=0.9,
    )

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"wav")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm) as mock_post:
        await provider.generate(TTSRequest(text="hello"))

    sent_payload = mock_post.call_args.kwargs["json"]
    assert sent_payload == {
        "text": "hello",
        "exaggeration": 0.7,
        "cfg_weight": 0.3,
        "temperature": 0.9,
    }


@pytest.mark.asyncio
async def test_generate_returns_err_on_non_200() -> None:
    provider = ChatterboxTTSProvider(base_url="http://localhost:5100")

    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="server error")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(TTSRequest(text="hello"))

    assert result.is_err()
