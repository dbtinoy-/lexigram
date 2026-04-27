import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import ImageRequest
from lexigram.multimedia.image.exceptions import (
    ImageGenerationAuthenticationError,
    ImageGenerationError,
)
from lexigram.multimedia.image.providers.openai import OpenAIImageProvider


@pytest.mark.asyncio
async def test_generate_decodes_base64_body_on_200() -> None:
    provider = OpenAIImageProvider(api_key="test-key")

    raw = b"\x89PNG....image-bytes"
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(
        return_value=b'{"data": [{"b64_json": "' + base64.b64encode(raw) + b'"}]}'
    )
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(
            ImageRequest(prompt="a red rose", width=1024, height=1024)
        )

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.bytes_data == raw
    assert asset.provider == "openai"


@pytest.mark.asyncio
async def test_generate_returns_err_on_401() -> None:
    provider = OpenAIImageProvider(api_key="bad-key")

    mock_resp = MagicMock()
    mock_resp.status = 401
    mock_resp.read = AsyncMock(return_value=b"unauthorized")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(
            ImageRequest(prompt="a red rose", width=1024, height=1024)
        )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), ImageGenerationAuthenticationError)


@pytest.mark.asyncio
async def test_generate_returns_err_on_unsupported_size() -> None:
    provider = OpenAIImageProvider(api_key="test-key", model="dall-e-3")

    result = await provider.generate(
        ImageRequest(prompt="a red rose", width=512, height=512)
    )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), ImageGenerationError)


@pytest.mark.asyncio
async def test_generate_returns_err_on_invalid_base64() -> None:
    provider = OpenAIImageProvider(api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(
        return_value=b'{"data": [{"b64_json": "not-valid-base64!!!"}]}'
    )
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(
            ImageRequest(prompt="a red rose", width=1024, height=1024)
        )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), ImageGenerationError)


@pytest.mark.asyncio
async def test_generate_uses_configurable_base_url() -> None:
    provider = OpenAIImageProvider(
        api_key="test-key", base_url="http://gateway.internal:8080"
    )

    raw = b"bytes"
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(
        return_value=b'{"data": [{"b64_json": "' + base64.b64encode(raw) + b'"}]}'
    )
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm) as mock_post:
        await provider.generate(ImageRequest(prompt="hello", width=1024, height=1024))

    called_url = mock_post.call_args.args[0]
    assert called_url == "http://gateway.internal:8080/v1/images/generations"
