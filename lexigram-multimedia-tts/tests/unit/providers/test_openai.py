from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import TTSRequest
from lexigram.multimedia.tts.providers.openai import OpenAITTSProvider


@pytest.mark.asyncio
async def test_generate_returns_ok_with_bytes() -> None:
    provider = OpenAITTSProvider(api_key="test-key")

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
    assert asset.provider == "openai"
    assert asset.mime_type == "audio/mpeg"


@pytest.mark.asyncio
async def test_generate_returns_err_on_401() -> None:
    provider = OpenAITTSProvider(api_key="bad-key")

    mock_resp = MagicMock()
    mock_resp.status = 401
    mock_resp.text = AsyncMock(return_value="unauthorized")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(TTSRequest(text="hello"))

    assert result.is_err()
    from lexigram.multimedia.tts.exceptions import TTSAuthenticationError

    assert isinstance(result.unwrap_err(), TTSAuthenticationError)


@pytest.mark.asyncio
async def test_generate_uses_configurable_base_url() -> None:
    provider = OpenAITTSProvider(
        api_key="test-key", base_url="http://gateway.internal:8080"
    )

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"bytes")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm) as mock_post:
        await provider.generate(TTSRequest(text="hello"))

    called_url = mock_post.call_args.args[0]
    assert called_url == "http://gateway.internal:8080/v1/audio/speech"
