from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import VideoRequest
from lexigram.multimedia.video.providers.local_http import LocalHttpVideoProvider


@pytest.mark.asyncio
async def test_generate_returns_ok_with_bytes_on_200() -> None:
    provider = LocalHttpVideoProvider(base_url="http://localhost:5004")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"....video-bytes")
    mock_resp.headers = {"Content-Type": "video/mp4"}
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(
            VideoRequest(prompt="a drone over the valley")
        )

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.has_bytes
    assert asset.bytes_data == b"....video-bytes"
    assert asset.mime_type == "video/mp4"
    assert asset.provider == "local-http"


@pytest.mark.asyncio
async def test_generate_returns_ok_with_uri_from_json_body() -> None:
    provider = LocalHttpVideoProvider(base_url="http://localhost:5004")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b'{"url": "http://localhost:5004/o.mp4"}')
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(
            VideoRequest(prompt="a drone over the valley")
        )

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.uri == "http://localhost:5004/o.mp4"
    assert not asset.has_bytes
    assert asset.provider == "local-http"


@pytest.mark.asyncio
async def test_generate_returns_err_on_non_200() -> None:
    provider = LocalHttpVideoProvider(base_url="http://localhost:5004")

    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="internal error")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm):
        result = await provider.generate(
            VideoRequest(prompt="a drone over the valley")
        )

    assert result.is_err()
