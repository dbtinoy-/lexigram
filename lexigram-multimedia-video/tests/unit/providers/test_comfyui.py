from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import VideoRequest
from lexigram.multimedia.video.exceptions import VideoGenerationError, VideoTimeoutError
from lexigram.multimedia.video.providers.comfyui import ComfyUiVideoProvider
from lexigram.serialization import dumps


def _mock_cm(resp: MagicMock) -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_generate_returns_err_when_image_uri_missing() -> None:
    provider = ComfyUiVideoProvider(
        base_url="http://localhost:8188", checkpoint="svd_xt_1_1.safetensors"
    )

    with patch("aiohttp.ClientSession.post") as mock_post:
        result = await provider.generate(VideoRequest(prompt="a drone shot"))

    mock_post.assert_not_called()
    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoGenerationError)


@pytest.mark.asyncio
async def test_generate_submits_polls_and_fetches_successfully() -> None:
    provider = ComfyUiVideoProvider(
        base_url="http://localhost:8188",
        checkpoint="svd_xt_1_1.safetensors",
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
                        "6": {
                            "gifs": [
                                {"filename": "x.mp4", "subfolder": "", "type": "output"}
                            ]
                        }
                    },
                }
            }
        )
    )
    view_resp = MagicMock()
    view_resp.status = 200
    view_resp.read = AsyncMock(return_value=b"video-bytes")

    with (
        patch("aiohttp.ClientSession.post", return_value=_mock_cm(submit_resp)),
        patch(
            "aiohttp.ClientSession.get",
            side_effect=[_mock_cm(history_resp), _mock_cm(view_resp)],
        ),
    ):
        result = await provider.generate(
            VideoRequest(prompt="ignored", image_uri="/data/frame.png")
        )

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.provider == "comfyui"
    assert asset.bytes_data == b"video-bytes"


@pytest.mark.asyncio
async def test_generate_fails_fast_on_execution_error_via_status_str() -> None:
    provider = ComfyUiVideoProvider(
        base_url="http://localhost:8188",
        checkpoint="svd_xt_1_1.safetensors",
        poll_interval=0.01,
    )

    submit_resp = MagicMock()
    submit_resp.status = 200
    submit_resp.read = AsyncMock(return_value=dumps({"prompt_id": "abc123"}))

    history_resp = MagicMock()
    history_resp.status = 200
    history_resp.read = AsyncMock(
        return_value=dumps(
            {"abc123": {"status": {"status_str": "error"}, "outputs": {}}}
        )
    )

    with (
        patch("aiohttp.ClientSession.post", return_value=_mock_cm(submit_resp)),
        patch("aiohttp.ClientSession.get", return_value=_mock_cm(history_resp)),
    ):
        result = await provider.generate(
            VideoRequest(prompt="ignored", image_uri="/data/frame.png")
        )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoGenerationError)


@pytest.mark.asyncio
async def test_generate_fails_fast_on_execution_error_via_messages() -> None:
    provider = ComfyUiVideoProvider(
        base_url="http://localhost:8188",
        checkpoint="svd_xt_1_1.safetensors",
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
                        "status_str": "success",
                        "messages": [["execution_error", {"node_id": "3"}]],
                    },
                    "outputs": {},
                }
            }
        )
    )

    with (
        patch("aiohttp.ClientSession.post", return_value=_mock_cm(submit_resp)),
        patch("aiohttp.ClientSession.get", return_value=_mock_cm(history_resp)),
    ):
        result = await provider.generate(
            VideoRequest(prompt="ignored", image_uri="/data/frame.png")
        )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoGenerationError)


@pytest.mark.asyncio
async def test_generate_times_out_when_never_completes() -> None:
    provider = ComfyUiVideoProvider(
        base_url="http://localhost:8188",
        checkpoint="svd_xt_1_1.safetensors",
        poll_interval=0.01,
        timeout=0.05,
    )

    submit_resp = MagicMock()
    submit_resp.status = 200
    submit_resp.read = AsyncMock(return_value=dumps({"prompt_id": "abc123"}))

    not_ready_resp = MagicMock()
    not_ready_resp.status = 200
    not_ready_resp.read = AsyncMock(return_value=dumps({}))

    with (
        patch("aiohttp.ClientSession.post", return_value=_mock_cm(submit_resp)),
        patch("aiohttp.ClientSession.get", return_value=_mock_cm(not_ready_resp)),
    ):
        result = await provider.generate(
            VideoRequest(prompt="ignored", image_uri="/data/frame.png")
        )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoTimeoutError)


@pytest.mark.asyncio
async def test_generate_returns_err_on_connection_error() -> None:
    provider = ComfyUiVideoProvider(
        base_url="http://localhost:8188", checkpoint="svd_xt_1_1.safetensors"
    )

    import aiohttp

    with patch("aiohttp.ClientSession.post", side_effect=aiohttp.ClientError()):
        result = await provider.generate(
            VideoRequest(prompt="ignored", image_uri="/data/frame.png")
        )

    assert result.is_err()
