from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from lexigram.contracts.multimedia.types import MusicRequest
from lexigram.multimedia.music.exceptions import (
    MusicGenerationAuthenticationError,
    MusicGenerationError,
)
from lexigram.multimedia.music.providers.stability_audio import (
    StabilityAudioMusicProvider,
)


def _mock_cm(resp: MagicMock) -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_generate_returns_ok_with_audio_bytes() -> None:
    provider = StabilityAudioMusicProvider(api_key="sk-test")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"ID3....audio-bytes")
    mock_resp.headers = {"Content-Type": "audio/mpeg"}

    with patch("aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)):
        result = await provider.generate(
            MusicRequest(prompt="an upbeat synthwave track", duration_seconds=24.0)
        )

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.provider == "stability-audio"
    assert asset.mime_type == "audio/mpeg"
    assert asset.bytes_data == b"ID3....audio-bytes"


@pytest.mark.asyncio
async def test_generate_sends_bearer_and_multipart_payload() -> None:
    provider = StabilityAudioMusicProvider(api_key="sk-test")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"audio-bytes")
    mock_resp.headers = {"Content-Type": "audio/wav"}

    with patch(
        "aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)
    ) as mock_post:
        with patch.object(
            aiohttp.FormData, "add_field", wraps=aiohttp.FormData.add_field
        ) as mock_add:
            result = await provider.generate(
                MusicRequest(
                    prompt="deep ambient pads",
                    duration_seconds=45,
                    format="wav",
                    extra={
                        "seed": 1234,
                        "steps": 60,
                        "cfg_scale": 7.5,
                        "model": "stable-audio-2.5",
                    },
                )
            )

    assert result.is_ok()
    call = mock_post.call_args
    assert call.kwargs["headers"]["Authorization"] == "Bearer sk-test"
    assert call.kwargs["headers"]["Accept"] == "audio/*"

    fields = {name: value for name, value, *_ in mock_add.call_args_list}
    assert fields["prompt"] == "deep ambient pads"
    assert fields["output_format"] == "wav"
    assert fields["duration"] == "45"
    assert fields["seed"] == "1234"
    assert fields["steps"] == "60"
    assert fields["cfg_scale"] == "7.5"
    assert fields["model"] == "stable-audio-2.5"


@pytest.mark.asyncio
async def test_generate_omits_extra_fields_when_absent() -> None:
    provider = StabilityAudioMusicProvider(api_key="sk-test")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"audio-bytes")
    mock_resp.headers = {"Content-Type": "audio/mpeg"}

    with patch(
        "aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)
    ) as mock_post:
        with patch.object(
            aiohttp.FormData, "add_field", wraps=aiohttp.FormData.add_field
        ) as mock_add:
            result = await provider.generate(MusicRequest(prompt="lo-fi beats"))

    assert result.is_ok()

    fields = {name for name, *_ in mock_add.call_args_list}
    assert {"prompt", "output_format", "duration"} <= fields
    assert "seed" not in fields
    assert "steps" not in fields
    assert "cfg_scale" not in fields
    assert "model" not in fields


@pytest.mark.asyncio
async def test_generate_returns_err_on_unsupported_format() -> None:
    provider = StabilityAudioMusicProvider(api_key="sk-test")

    result = await provider.generate(MusicRequest(prompt="lo-fi beats", format="flac"))

    assert result.is_err()
    error = result.unwrap_err()
    assert isinstance(error, MusicGenerationError)
    assert "flac" in str(error)


@pytest.mark.asyncio
async def test_generate_returns_auth_error_on_401() -> None:
    provider = StabilityAudioMusicProvider(api_key="sk-test")

    mock_resp = MagicMock()
    mock_resp.status = 401
    mock_resp.text = AsyncMock(return_value="unauthorized")
    mock_resp.headers = {}

    with patch("aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)):
        result = await provider.generate(MusicRequest(prompt="lo-fi beats"))

    assert result.is_err()
    assert isinstance(result.unwrap_err(), MusicGenerationAuthenticationError)


@pytest.mark.asyncio
async def test_generate_returns_err_on_non_200() -> None:
    provider = StabilityAudioMusicProvider(api_key="sk-test")

    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="server error")
    mock_resp.headers = {}

    with patch("aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)):
        result = await provider.generate(MusicRequest(prompt="lo-fi beats"))

    assert result.is_err()
    assert "500" in str(result.unwrap_err())


@pytest.mark.asyncio
async def test_generate_returns_err_on_connection_error() -> None:
    provider = StabilityAudioMusicProvider(api_key="sk-test")

    with patch("aiohttp.ClientSession.post", side_effect=aiohttp.ClientError()):
        result = await provider.generate(MusicRequest(prompt="lo-fi beats"))

    assert result.is_err()