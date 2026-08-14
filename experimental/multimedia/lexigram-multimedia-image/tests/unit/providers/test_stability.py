import base64

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
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


@pytest.mark.asyncio
async def test_generate_uses_image_to_image_when_reference_image_set() -> None:
    provider = StabilityImageProvider(api_key="key")

    raw = b"\x89PNG....edited-bytes"
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=base64.b64encode(raw))
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm) as mock_post:
        result = await provider.generate(
            ImageRequest(
                prompt="the same character, different pose",
                reference_image=b"reference-bytes",
                reference_mime_type="image/png",
            )
        )

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.bytes_data == raw
    _, kwargs = mock_post.call_args
    assert isinstance(kwargs["data"], aiohttp.FormData)


@pytest.mark.asyncio
async def test_generate_default_reference_strength_is_sent_as_point_65() -> None:
    provider = StabilityImageProvider(api_key="key")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=base64.b64encode(b"bytes"))
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_form = MagicMock()

    with (
        patch("aiohttp.ClientSession.post", return_value=mock_cm),
        patch("aiohttp.FormData", return_value=mock_form),
    ):
        result = await provider.generate(
            ImageRequest(prompt="x", reference_image=b"ref", reference_mime_type="image/png")
        )

    assert result.is_ok()
    mock_form.add_field.assert_any_call("strength", "0.65")


@pytest.mark.asyncio
async def test_generate_reference_strength_read_from_extra() -> None:
    provider = StabilityImageProvider(api_key="key")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=base64.b64encode(b"bytes"))
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_form = MagicMock()

    with (
        patch("aiohttp.ClientSession.post", return_value=mock_cm),
        patch("aiohttp.FormData", return_value=mock_form),
    ):
        result = await provider.generate(
            ImageRequest(
                prompt="x",
                reference_image=b"ref",
                reference_mime_type="image/png",
                extra={"reference_strength": 0.3},
            )
        )

    assert result.is_ok()
    mock_form.add_field.assert_any_call("strength", "0.3")


@pytest.mark.asyncio
async def test_generate_without_reference_image_still_sends_json() -> None:
    provider = StabilityImageProvider(api_key="key")

    raw = b"bytes"
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(return_value=base64.b64encode(raw))
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm) as mock_post:
        await provider.generate(ImageRequest(prompt="a red rose"))

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["prompt"] == "a red rose"
