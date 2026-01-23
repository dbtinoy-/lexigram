from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import TTSRequest
from lexigram.multimedia.tts.providers.local_http import LocalHttpTTSProvider


@pytest.mark.asyncio
async def test_generate_returns_ok_with_bytes_on_200() -> None:
    provider = LocalHttpTTSProvider(base_url="http://localhost:5002")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"RIFF....audio-bytes")
    mock_resp.headers = {"Content-Type": "audio/wav"}
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(TTSRequest(text="hello world"))

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.has_bytes
    assert asset.bytes_data == b"RIFF....audio-bytes"
    assert asset.mime_type == "audio/wav"
    assert asset.provider == "local-http"


@pytest.mark.asyncio
async def test_generate_returns_err_on_non_200() -> None:
    provider = LocalHttpTTSProvider(base_url="http://localhost:5002")

    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="internal error")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(TTSRequest(text="hello world"))

    assert result.is_err()
