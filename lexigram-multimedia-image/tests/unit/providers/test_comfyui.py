from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import ImageRequest
from lexigram.multimedia.image.exceptions import ImageGenerationError, ImageTimeoutError
from lexigram.multimedia.image.providers.comfyui import ComfyUiImageProvider
from lexigram.serialization import dumps


def _mock_cm(mock_resp: MagicMock) -> MagicMock:
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm


@pytest.mark.asyncio
async def test_generate_submits_polls_and_fetches_on_success() -> None:
    provider = ComfyUiImageProvider(
        base_url="http://localhost:8188",
        checkpoint="sd_xl_base_1.0.safetensors",
        poll_interval=0.01,
    )

    submit_resp = MagicMock()
    submit_resp.status = 200
    submit_resp.read = AsyncMock(return_value=dumps({"prompt_id": "abc123"}))

    history_resp = MagicMock()
    history_resp.status = 200
    history_resp.read = AsyncMock(
        return_value=dumps(
            {
                "abc123": {
                    "status": {"completed": True, "status_str": "success"},
                    "outputs": {
                        "9": {
                            "images": [
                                {
                                    "filename": "lexigram_00001.png",
                                    "subfolder": "",
                                    "type": "output",
                                }
                            ]
                        }
                    },
                }
            }
        )
    )

    view_resp = MagicMock()
    view_resp.status = 200
    view_resp.read = AsyncMock(return_value=b"\x89PNG....image-bytes")

    with (
        patch("aiohttp.ClientSession.post", return_value=_mock_cm(submit_resp)),
        patch(
            "aiohttp.ClientSession.get",
            side_effect=[_mock_cm(history_resp), _mock_cm(view_resp)],
        ),
    ):
        result = await provider.generate(
            ImageRequest(prompt="a red rose", width=1024, height=1024)
        )

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.bytes_data == b"\x89PNG....image-bytes"
    assert asset.provider == "comfyui"


@pytest.mark.asyncio
async def test_generate_fails_fast_on_execution_error() -> None:
    provider = ComfyUiImageProvider(
        base_url="http://localhost:8188",
        checkpoint="sd_xl_base_1.0.safetensors",
        poll_interval=0.01,
    )

    submit_resp = MagicMock()
    submit_resp.status = 200
    submit_resp.read = AsyncMock(return_value=dumps({"prompt_id": "abc123"}))

    history_resp = MagicMock()
    history_resp.status = 200
    history_resp.read = AsyncMock(
        return_value=dumps(
            {"abc123": {"status": {"status_str": "error", "completed": False}}}
        )
    )

    with (
        patch("aiohttp.ClientSession.post", return_value=_mock_cm(submit_resp)),
        patch("aiohttp.ClientSession.get", return_value=_mock_cm(history_resp)),
    ):
        result = await provider.generate(
            ImageRequest(prompt="a red rose", width=1024, height=1024)
        )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), ImageGenerationError)


@pytest.mark.asyncio
async def test_generate_fails_fast_on_execution_error_via_messages() -> None:
    """Some ComfyUI versions signal failure only through status["messages"],
    without ever setting status_str to "error" — spec §4's second failure path.
    """
    provider = ComfyUiImageProvider(
        base_url="http://localhost:8188",
        checkpoint="sd_xl_base_1.0.safetensors",
        poll_interval=0.01,
    )

    submit_resp = MagicMock()
    submit_resp.status = 200
    submit_resp.read = AsyncMock(return_value=dumps({"prompt_id": "abc123"}))

    history_resp = MagicMock()
    history_resp.status = 200
    history_resp.read = AsyncMock(
        return_value=dumps(
            {
                "abc123": {
                    "status": {
                        "completed": False,
                        "messages": [["execution_error", {"node_id": "3"}]],
                    }
                }
            }
        )
    )

    with (
        patch("aiohttp.ClientSession.post", return_value=_mock_cm(submit_resp)),
        patch("aiohttp.ClientSession.get", return_value=_mock_cm(history_resp)),
    ):
        result = await provider.generate(
            ImageRequest(prompt="a red rose", width=1024, height=1024)
        )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), ImageGenerationError)


@pytest.mark.asyncio
async def test_generate_times_out_when_never_completes() -> None:
    provider = ComfyUiImageProvider(
        base_url="http://localhost:8188",
        checkpoint="sd_xl_base_1.0.safetensors",
        poll_interval=0.01,
        timeout=0.05,
    )

    not_ready_resp = MagicMock()
    not_ready_resp.status = 200
    not_ready_resp.read = AsyncMock(return_value=dumps({}))

    submit_resp = MagicMock()
    submit_resp.status = 200
    submit_resp.read = AsyncMock(return_value=dumps({"prompt_id": "abc123"}))

    with (
        patch("aiohttp.ClientSession.post", return_value=_mock_cm(submit_resp)),
        patch("aiohttp.ClientSession.get", return_value=_mock_cm(not_ready_resp)),
    ):
        result = await provider.generate(
            ImageRequest(prompt="a red rose", width=1024, height=1024)
        )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), ImageTimeoutError)


@pytest.mark.asyncio
async def test_generate_returns_err_on_connection_error() -> None:
    provider = ComfyUiImageProvider(
        base_url="http://localhost:8188",
        checkpoint="sd_xl_base_1.0.safetensors",
    )

    import aiohttp

    with patch("aiohttp.ClientSession.post", side_effect=aiohttp.ClientError()):
        result = await provider.generate(
            ImageRequest(prompt="a red rose", width=1024, height=1024)
        )

    assert result.is_err()


@pytest.mark.asyncio
async def test_generate_sends_negative_prompt_from_extra() -> None:
    provider = ComfyUiImageProvider(
        base_url="http://localhost:8188",
        checkpoint="sd_xl_base_1.0.safetensors",
        poll_interval=0.01,
    )

    submit_resp = MagicMock()
    submit_resp.status = 200
    submit_resp.read = AsyncMock(return_value=dumps({"prompt_id": "abc123"}))

    history_resp = MagicMock()
    history_resp.status = 200
    history_resp.read = AsyncMock(
        return_value=dumps(
            {
                "abc123": {
                    "status": {"completed": True, "status_str": "success"},
                    "outputs": {
                        "9": {
                            "images": [
                                {"filename": "x.png", "subfolder": "", "type": "output"}
                            ]
                        }
                    },
                }
            }
        )
    )
    view_resp = MagicMock()
    view_resp.status = 200
    view_resp.read = AsyncMock(return_value=b"bytes")

    with (
        patch(
            "aiohttp.ClientSession.post", return_value=_mock_cm(submit_resp)
        ) as mock_post,
        patch(
            "aiohttp.ClientSession.get",
            side_effect=[_mock_cm(history_resp), _mock_cm(view_resp)],
        ),
    ):
        await provider.generate(
            ImageRequest(
                prompt="a red rose",
                width=1024,
                height=1024,
                extra={"negative_prompt": "blurry, low quality"},
            )
        )

    sent_workflow = mock_post.call_args.kwargs["json"]["prompt"]
    assert sent_workflow["7"]["inputs"]["text"] == "blurry, low quality"


@pytest.mark.asyncio
async def test_generate_returns_err_when_reference_image_set() -> None:
    provider = ComfyUiImageProvider(
        base_url="http://localhost:8188",
        checkpoint="sd_xl_base_1.0.safetensors",
        poll_interval=0.01,
    )

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
