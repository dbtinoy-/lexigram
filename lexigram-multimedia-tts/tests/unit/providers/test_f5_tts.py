from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import TTSRequest
from lexigram.multimedia.tts.exceptions import TTSError
from lexigram.multimedia.tts.providers.f5_tts import F5TTSProvider


@pytest.mark.asyncio
async def test_generate_returns_ok_with_wav_bytes() -> None:
    provider = F5TTSProvider(base_url="http://localhost:5102")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"RIFF....wav-bytes")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(
            TTSRequest(
                text="hello world",
                extra={
                    "reference_audio_uri": "file:///tmp/ref.wav",
                    "reference_text": "reference transcript",
                },
            )
        )

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.mime_type == "audio/wav"
    assert asset.provider == "f5-tts"


@pytest.mark.asyncio
async def test_generate_returns_err_when_reference_audio_uri_missing() -> None:
    provider = F5TTSProvider(base_url="http://localhost:5102")

    result = await provider.generate(
        TTSRequest(text="hello", extra={"reference_text": "reference transcript"})
    )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), TTSError)


@pytest.mark.asyncio
async def test_generate_returns_err_when_reference_text_missing() -> None:
    provider = F5TTSProvider(base_url="http://localhost:5102")

    result = await provider.generate(
        TTSRequest(text="hello", extra={"reference_audio_uri": "file:///tmp/ref.wav"})
    )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), TTSError)


@pytest.mark.asyncio
async def test_generate_returns_err_on_non_200() -> None:
    provider = F5TTSProvider(base_url="http://localhost:5102")

    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="server error")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(
            TTSRequest(
                text="hello",
                extra={
                    "reference_audio_uri": "file:///tmp/ref.wav",
                    "reference_text": "hi",
                },
            )
        )

    assert result.is_err()
