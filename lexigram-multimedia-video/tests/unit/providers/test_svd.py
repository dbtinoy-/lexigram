from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import VideoRequest
from lexigram.multimedia.video.exceptions import VideoGenerationError
from lexigram.multimedia.video.providers.svd import SVDVideoProvider


@pytest.mark.asyncio
async def test_generate_returns_ok_with_bytes() -> None:
    provider = SVDVideoProvider(base_url="http://localhost:5202")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"mp4-bytes")
    mock_resp.headers = {"Content-Type": "video/mp4"}
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(
            VideoRequest(prompt="ignored", image_uri="file:///tmp/frame.png")
        )

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.provider == "svd"


@pytest.mark.asyncio
async def test_generate_returns_err_when_image_uri_missing() -> None:
    provider = SVDVideoProvider(base_url="http://localhost:5202")

    with patch("aiohttp.ClientSession.post") as mock_post:
        result = await provider.generate(VideoRequest(prompt="a drone shot"))

    mock_post.assert_not_called()
    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoGenerationError)


@pytest.mark.asyncio
async def test_generate_returns_err_on_non_200() -> None:
    provider = SVDVideoProvider(base_url="http://localhost:5202")

    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="server error")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(
            VideoRequest(prompt="x", image_uri="file:///tmp/frame.png")
        )

    assert result.is_err()


@pytest.mark.asyncio
async def test_generate_returns_err_on_connection_error() -> None:
    provider = SVDVideoProvider(base_url="http://localhost:5202")

    import aiohttp

    with patch("aiohttp.ClientSession.post", side_effect=aiohttp.ClientError()):
        result = await provider.generate(
            VideoRequest(prompt="x", image_uri="file:///tmp/frame.png")
        )

    assert result.is_err()
