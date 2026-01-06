from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import TTSRequest
from lexigram.multimedia.audio_tts.providers.elevenlabs import ElevenLabsTTSProvider


@pytest.mark.asyncio
async def test_generate_returns_ok_with_bytes() -> None:
    provider = ElevenLabsTTSProvider(api_key="test-key", voice_id="21m00Tcm4TlvDq8ikWAM")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"mp3-bytes-here")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(TTSRequest(text="hello"))

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.has_bytes
    assert asset.provider == "elevenlabs"
    assert asset.mime_type == "audio/mpeg"


@pytest.mark.asyncio
async def test_generate_returns_err_on_401() -> None:
    provider = ElevenLabsTTSProvider(api_key="bad-key", voice_id="21m00Tcm4TlvDq8ikWAM")

    mock_resp = MagicMock()
    mock_resp.status = 401
    mock_resp.text = AsyncMock(return_value="unauthorized")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(TTSRequest(text="hello"))

    assert result.is_err()
