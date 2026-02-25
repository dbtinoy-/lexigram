from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import TTSRequest
from lexigram.multimedia.tts.exceptions import TTSError
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


def _mock_json_response(body: bytes) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=body)
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm


def _mock_audio_response() -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"mp3-cloned-voice")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm


@pytest.mark.asyncio
async def test_generate_with_reference_audio_sends_cloning_metadata() -> None:
    provider = OpenAITTSProvider(api_key="test-key")
    json_cm = _mock_json_response(b'{"audio": "https://cdn.example.com/voice.mp3"}')
    audio_cm = _mock_audio_response()
    with (
        patch("aiohttp.ClientSession.post", return_value=json_cm) as mock_post,
        patch("aiohttp.ClientSession.get", return_value=audio_cm) as mock_get,
    ):
        result = await provider.generate(
            TTSRequest(
                text="hello",
                reference_audio_uri="https://cdn.example.com/ref.wav",
            )
        )
    assert result.is_ok()
    first_payload = mock_post.call_args.kwargs["json"]
    assert first_payload["metadata"] == {
        "audio_url": "https://cdn.example.com/ref.wav",
        "should_use_prompt_for_emotion": True,
    }
    assert "voice" not in first_payload
    second_url = mock_get.call_args.args[0]
    assert second_url == "https://cdn.example.com/voice.mp3"
    assert result.unwrap().bytes_data == b"mp3-cloned-voice"


@pytest.mark.asyncio
async def test_generate_with_emotion_sets_emotion_prompt() -> None:
    provider = OpenAITTSProvider(api_key="test-key")
    json_cm = _mock_json_response(b'{"audio": "https://cdn.example.com/voice.mp3"}')
    audio_cm = _mock_audio_response()
    with (
        patch("aiohttp.ClientSession.post", return_value=json_cm) as mock_post,
        patch("aiohttp.ClientSession.get", return_value=audio_cm),
    ):
        result = await provider.generate(
            TTSRequest(
                text="hello",
                reference_audio_uri="https://cdn.example.com/ref.wav",
                emotion="excited",
            )
        )
    assert result.is_ok()
    metadata = mock_post.call_args.kwargs["json"]["metadata"]
    assert metadata["emotion_prompt"] == "excited"


@pytest.mark.asyncio
async def test_generate_without_reference_audio_sends_voice_no_metadata() -> None:
    provider = OpenAITTSProvider(api_key="test-key")
    with patch("aiohttp.ClientSession.post", return_value=_mock_audio_response()) as mock_post:
        result = await provider.generate(
            TTSRequest(text="hello", voice="nova")
        )
    assert result.is_ok()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["voice"] == "nova"
    assert "metadata" not in payload


@pytest.mark.asyncio
async def test_generate_returns_err_when_json_response_missing_audio() -> None:
    provider = OpenAITTSProvider(api_key="test-key")
    with patch("aiohttp.ClientSession.post", return_value=_mock_json_response(b"{}")) as mock_post:
        result = await provider.generate(
            TTSRequest(text="hello", reference_audio_uri="https://cdn.example.com/ref.wav")
        )
    assert result.is_err()
    assert isinstance(result.unwrap_err(), TTSError)
    assert mock_post.call_count == 1


@pytest.mark.asyncio
async def test_generate_returns_err_when_audio_fetch_fails() -> None:
    provider = OpenAITTSProvider(api_key="test-key")
    bad_resp = MagicMock()
    bad_resp.status = 500
    bad_resp.text = AsyncMock(return_value="boom")
    bad_cm = MagicMock()
    bad_cm.__aenter__ = AsyncMock(return_value=bad_resp)
    bad_cm.__aexit__ = AsyncMock(return_value=False)
    json_cm = _mock_json_response(b'{"audio": "https://cdn.example.com/voice.mp3"}')
    with (
        patch("aiohttp.ClientSession.post", return_value=json_cm),
        patch("aiohttp.ClientSession.get", return_value=bad_cm),
    ):
        result = await provider.generate(
            TTSRequest(text="hello", reference_audio_uri="https://cdn.example.com/ref.wav")
        )
    assert result.is_err()
    assert isinstance(result.unwrap_err(), TTSError)
