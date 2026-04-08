import base64

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import ImageRequest
from lexigram.multimedia.image.exceptions import (
    ImageGenerationAuthenticationError,
    ImageGenerationError,
)
from lexigram.multimedia.image.providers.stability import StabilityImageProvider


@pytest.mark.asyncio
async def test_generate_decodes_base64_body_on_200() -> None:
    provider = StabilityImageProvider(api_key="key")

    raw = b"\x89PNG....image-bytes"
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=base64.b64encode(raw))
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(
            ImageRequest(prompt="a red rose", format="png")
        )

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.bytes_data == raw
    assert asset.mime_type == "image/png"
    assert asset.provider == "stability"


@pytest.mark.asyncio
async def test_generate_returns_err_on_401() -> None:
    provider = StabilityImageProvider(api_key="bad")

    mock_resp = MagicMock()
    mock_resp.status = 401
    mock_resp.text = AsyncMock(return_value="unauthorized")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(ImageRequest(prompt="a red rose"))

    assert result.is_err()
    assert isinstance(result.unwrap_err(), ImageGenerationAuthenticationError)


@pytest.mark.asyncio
async def test_generate_returns_err_on_invalid_base64() -> None:
    provider = StabilityImageProvider(api_key="key")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"not-valid-base64!!!")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(ImageRequest(prompt="a red rose"))

    assert result.is_err()
    assert isinstance(result.unwrap_err(), ImageGenerationError)
