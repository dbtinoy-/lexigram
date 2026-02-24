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


@pytest.mark.asyncio
async def test_generate_uses_edit_endpoint_when_reference_image_set() -> None:
    provider = OpenAIImageProvider(api_key="test-key", model="dall-e-2")

    raw = b"\x89PNG....edited-bytes"
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(
        return_value=b'{"data": [{"b64_json": "' + base64.b64encode(raw) + b'"}]}'
    )
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=mock_cm) as mock_post:
        result = await provider.generate(
            ImageRequest(
                prompt="the same cat wearing a hat",
                width=1024,
                height=1024,
                reference_image=b"reference-bytes",
                reference_mime_type="image/png",
            )
        )

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.bytes_data == raw
    called_url = mock_post.call_args.args[0]
    assert called_url == "https://api.openai.com/v1/images/edits"


@pytest.mark.asyncio
async def test_generate_returns_err_when_model_not_edit_capable() -> None:
    provider = OpenAIImageProvider(api_key="test-key", model="dall-e-3")

    result = await provider.generate(
        ImageRequest(
            prompt="the same cat wearing a hat",
            width=1024,
            height=1024,
            reference_image=b"reference-bytes",
            reference_mime_type="image/png",
        )
    )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), ImageGenerationError)
    assert "does not support reference-image conditioning" in str(result.unwrap_err())


@pytest.mark.asyncio
async def test_generate_without_reference_image_still_uses_generations_endpoint() -> None:
    provider = OpenAIImageProvider(api_key="test-key")

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
    assert called_url == "https://api.openai.com/v1/images/generations"


def _mock_ok_response(raw: bytes = b"\x89PNG....image-bytes") -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read = AsyncMock(
        return_value=b'{"data": [{"b64_json": "' + base64.b64encode(raw) + b'"}]}'
    )
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm


@pytest.mark.asyncio
async def test_generate_aspect_ratio_9_16_resolves_size() -> None:
    provider = OpenAIImageProvider(api_key="test-key")
    with patch("aiohttp.ClientSession.post", return_value=_mock_ok_response()) as mock_post:
        result = await provider.generate(
            ImageRequest(prompt="a red rose", extra={"aspect_ratio": "9:16"})
        )
    assert result.is_ok()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["size"] == "1024x1792"


@pytest.mark.asyncio
async def test_generate_aspect_ratio_16_9_resolves_size() -> None:
    provider = OpenAIImageProvider(api_key="test-key")
    with patch("aiohttp.ClientSession.post", return_value=_mock_ok_response()) as mock_post:
        result = await provider.generate(
            ImageRequest(prompt="a red rose", extra={"aspect_ratio": "16:9"})
        )
    assert result.is_ok()
    assert mock_post.call_args.kwargs["json"]["size"] == "1792x1024"


@pytest.mark.asyncio
async def test_generate_aspect_ratio_normalizes_dash_and_fullwidth() -> None:
    provider = OpenAIImageProvider(api_key="test-key")
    with patch("aiohttp.ClientSession.post", return_value=_mock_ok_response()) as mock_post:
        result = await provider.generate(
            ImageRequest(prompt="a red rose", extra={"aspect_ratio": "9-16"})
        )
    assert result.is_ok()
    assert mock_post.call_args.kwargs["json"]["size"] == "1024x1792"


@pytest.mark.asyncio
async def test_generate_unknown_aspect_ratio_returns_err() -> None:
    provider = OpenAIImageProvider(api_key="test-key")
    with patch("aiohttp.ClientSession.post") as mock_post:
        result = await provider.generate(
            ImageRequest(prompt="a red rose", extra={"aspect_ratio": "21:9"})
        )
    assert result.is_err()
    assert isinstance(result.unwrap_err(), ImageGenerationError)
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_generate_size_override_beats_aspect_ratio() -> None:
    provider = OpenAIImageProvider(api_key="test-key")
    with patch("aiohttp.ClientSession.post", return_value=_mock_ok_response()) as mock_post:
        result = await provider.generate(
            ImageRequest(
                prompt="a red rose",
                width=1024,
                height=1024,
                extra={"aspect_ratio": "16:9", "size": "1024x1792"},
            )
        )
    assert result.is_ok()
    assert mock_post.call_args.kwargs["json"]["size"] == "1024x1792"


@pytest.mark.asyncio
async def test_generate_generation_extras_passthrough() -> None:
    provider = OpenAIImageProvider(api_key="test-key")
    with patch("aiohttp.ClientSession.post", return_value=_mock_ok_response()) as mock_post:
        result = await provider.generate(
            ImageRequest(
                prompt="a red rose",
                extra={
                    "quality": "high",
                    "output_format": "png",
                    "watermark": False,
                },
            )
        )
    assert result.is_ok()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["quality"] == "high"
    assert payload["output_format"] == "png"
    assert payload["watermark"] is False


@pytest.mark.asyncio
async def test_generate_aspect_ratio_respects_model_supported_sizes() -> None:
    provider = OpenAIImageProvider(api_key="test-key", model="dall-e-2")
    with patch("aiohttp.ClientSession.post") as mock_post:
        result = await provider.generate(
            ImageRequest(prompt="a red rose", extra={"aspect_ratio": "9:16"})
        )
    assert result.is_err()
    assert isinstance(result.unwrap_err(), ImageGenerationError)
    assert "supported sizes" in str(result.unwrap_err())
    mock_post.assert_not_called()
