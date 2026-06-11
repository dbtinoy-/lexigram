import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import MediaAsset, UpscaleRequest
from lexigram.multimedia.upscale.providers.real_esrgan import RealEsrganUpscaleProvider


def _mock_cm(resp: MagicMock) -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_upscale_returns_ok_with_bytes() -> None:
    provider = RealEsrganUpscaleProvider(base_url="http://localhost:5400")
    source = MediaAsset(mime_type="image/png", provider="test", bytes_data=b"source-png")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"upscaled-png")
    mock_resp.headers = {"Content-Type": "image/png"}

    with patch(
        "aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)
    ) as mock_post:
        result = await provider.upscale(UpscaleRequest(asset=source, scale_factor=4))

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.provider == "real-esrgan"
    assert asset.mime_type == "image/png"
    sent_payload = mock_post.call_args.kwargs["json"]
    assert base64.b64decode(sent_payload["image_bytes"]) == b"source-png"
    assert sent_payload["scale_factor"] == 4


@pytest.mark.asyncio
async def test_upscale_returns_err_on_non_200() -> None:
    provider = RealEsrganUpscaleProvider(base_url="http://localhost:5400")
    source = MediaAsset(mime_type="image/png", provider="test", bytes_data=b"source-png")

    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="server error")

    with patch("aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)):
        result = await provider.upscale(UpscaleRequest(asset=source))

    assert result.is_err()


@pytest.mark.asyncio
async def test_upscale_returns_err_on_disallowed_mime_type() -> None:
    provider = RealEsrganUpscaleProvider(base_url="http://localhost:5400")
    source = MediaAsset(mime_type="application/pdf", provider="test", bytes_data=b"x")

    with patch(
        "aiohttp.ClientSession.post", side_effect=AssertionError("fetch attempted")
    ):
        result = await provider.upscale(UpscaleRequest(asset=source))

    assert result.is_err()
    assert "media allowlist" in str(result.unwrap_err())


@pytest.mark.asyncio
async def test_upscale_returns_err_on_connection_error() -> None:
    provider = RealEsrganUpscaleProvider(base_url="http://localhost:5400")
    source = MediaAsset(mime_type="image/png", provider="test", bytes_data=b"source-png")

    import aiohttp

    with patch("aiohttp.ClientSession.post", side_effect=aiohttp.ClientError()):
        result = await provider.upscale(UpscaleRequest(asset=source))

    assert result.is_err()
