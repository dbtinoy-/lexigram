from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import VideoRequest
from lexigram.multimedia.video.providers.cogvideox import CogVideoXVideoProvider


@pytest.mark.asyncio
async def test_generate_returns_ok_with_bytes() -> None:
    provider = CogVideoXVideoProvider(base_url="http://localhost:5201")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"mp4-bytes")
    mock_resp.headers = {"Content-Type": "video/mp4"}
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(VideoRequest(prompt="a drone over the valley"))

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.provider == "cogvideox"
    assert asset.mime_type == "video/mp4"


@pytest.mark.asyncio
async def test_generate_returns_err_on_non_200() -> None:
    provider = CogVideoXVideoProvider(base_url="http://localhost:5201")

    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="server error")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(VideoRequest(prompt="hello"))

    assert result.is_err()


@pytest.mark.asyncio
async def test_generate_returns_err_on_connection_error() -> None:
    provider = CogVideoXVideoProvider(base_url="http://localhost:5201")

    import aiohttp

    with patch("aiohttp.ClientSession.post", side_effect=aiohttp.ClientError()):
        result = await provider.generate(VideoRequest(prompt="hello"))

    assert result.is_err()


@pytest.mark.asyncio
async def test_generate_forwards_optional_image_uri_without_validating_it() -> None:
    provider = CogVideoXVideoProvider(base_url="http://localhost:5201")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"mp4-bytes")
    mock_resp.headers = {"Content-Type": "video/mp4"}
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm) as mock_post:
        await provider.generate(
            VideoRequest(prompt="hello", image_uri="file:///tmp/frame.png")
        )

    assert mock_post.call_args.kwargs["json"]["image_uri"] == "file:///tmp/frame.png"
