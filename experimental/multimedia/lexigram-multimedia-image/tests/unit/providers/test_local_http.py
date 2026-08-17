from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import ImageRequest
from lexigram.multimedia.image.exceptions import ImageGenerationError
from lexigram.multimedia.image.providers.local_http import LocalHttpImageProvider


@pytest.mark.asyncio
async def test_generate_returns_ok_with_bytes_on_200() -> None:
    provider = LocalHttpImageProvider(base_url="http://localhost:5005")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"\x89PNG....image-bytes")
    mock_resp.headers = {"Content-Type": "image/png"}
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(
            ImageRequest(prompt="a red rose", width=1024, height=1024)
        )

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.has_bytes
    assert asset.bytes_data == b"\x89PNG....image-bytes"
    assert asset.mime_type == "image/png"
    assert asset.provider == "local-http"


@pytest.mark.asyncio
async def test_generate_returns_err_on_non_200() -> None:
    provider = LocalHttpImageProvider(base_url="http://localhost:5005")

    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="internal error")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(ImageRequest(prompt="a red rose"))

    assert result.is_err()


@pytest.mark.asyncio
async def test_generate_returns_err_when_reference_image_set() -> None:
    provider = LocalHttpImageProvider(base_url="http://localhost:9000")

    result = await provider.generate(
        ImageRequest(
            prompt="a cat",
            reference_image=b"reference-bytes",
            reference_mime_type="image/png",
        )
    )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), ImageGenerationError)
    assert "does not support reference-image conditioning" in str(result.unwrap_err())
