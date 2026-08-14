import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import InterpolationRequest, MediaAsset
from lexigram.multimedia.interpolate.providers.rife import RifeInterpolationProvider


def _mock_cm(resp: MagicMock) -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_interpolate_returns_ok_with_bytes() -> None:
    provider = RifeInterpolationProvider(base_url="http://localhost:5500")
    frame_a = MediaAsset(mime_type="image/png", provider="test", bytes_data=b"frame-a")
    frame_b = MediaAsset(mime_type="image/png", provider="test", bytes_data=b"frame-b")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=b"midpoint-png")
    mock_resp.headers = {"Content-Type": "image/png"}

    with patch(
        "aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)
    ) as mock_post:
        result = await provider.interpolate(
            InterpolationRequest(frame_a=frame_a, frame_b=frame_b)
        )

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.provider == "rife"
    assert asset.mime_type == "image/png"
    sent_payload = mock_post.call_args.kwargs["json"]
    assert base64.b64decode(sent_payload["frame_a_bytes"]) == b"frame-a"
    assert base64.b64decode(sent_payload["frame_b_bytes"]) == b"frame-b"


@pytest.mark.asyncio
async def test_interpolate_returns_err_on_non_200() -> None:
    provider = RifeInterpolationProvider(base_url="http://localhost:5500")
    frame_a = MediaAsset(mime_type="image/png", provider="test", bytes_data=b"a")
    frame_b = MediaAsset(mime_type="image/png", provider="test", bytes_data=b"b")

    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="server error")

    with patch("aiohttp.ClientSession.post", return_value=_mock_cm(mock_resp)):
        result = await provider.interpolate(
            InterpolationRequest(frame_a=frame_a, frame_b=frame_b)
        )

    assert result.is_err()


@pytest.mark.asyncio
async def test_interpolate_returns_err_on_connection_error() -> None:
    provider = RifeInterpolationProvider(base_url="http://localhost:5500")
    frame_a = MediaAsset(mime_type="image/png", provider="test", bytes_data=b"a")
    frame_b = MediaAsset(mime_type="image/png", provider="test", bytes_data=b"b")

    import aiohttp

    with patch("aiohttp.ClientSession.post", side_effect=aiohttp.ClientError()):
        result = await provider.interpolate(
            InterpolationRequest(frame_a=frame_a, frame_b=frame_b)
        )

    assert result.is_err()
