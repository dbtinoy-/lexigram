from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import VideoMode, VideoRequest
from lexigram.multimedia.video.exceptions import (
    VideoGenerationAuthenticationError,
    VideoGenerationError,
    VideoTimeoutError,
)
from lexigram.multimedia.video.providers.openai import OpenAIVideoProvider


def _mock_resp(status: int, body: str) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.text = AsyncMock(return_value=body)
    return mock_resp


@contextmanager
def _patch_ok_gateway() -> Iterator[MagicMock]:
    submit_cm = MagicMock()
    submit_cm.__aenter__ = AsyncMock(return_value=_mock_resp(200, '{"id": "vid-1"}'))
    submit_cm.__aexit__ = AsyncMock(return_value=False)

    poll_cm = MagicMock()
    poll_cm.__aenter__ = AsyncMock(
        return_value=_mock_resp(
            200, '{"status": "completed", "url": "https://cdn.example/v.mp4"}'
        )
    )
    poll_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("aiohttp.ClientSession.post", return_value=submit_cm) as mock_post,
        patch("aiohttp.ClientSession.get", return_value=poll_cm),
    ):
        yield mock_post


@pytest.mark.asyncio
async def test_generate_payload_uses_duration_resolution_and_model() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=5)
    with _patch_ok_gateway() as mock_post:
        result = await provider.generate(
            VideoRequest(prompt="a drone over the valley", duration_seconds=6)
        )
    assert result.is_ok()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["duration"] == 6
    assert payload["resolution"] == "1280x720"
    assert payload["model"] == "sora-2"


@pytest.mark.asyncio
async def test_generate_request_model_overrides_config_model() -> None:
    provider = OpenAIVideoProvider(
        api_key="key", model="seedance-2.0", poll_interval=0.01, max_polls=5
    )
    with _patch_ok_gateway() as mock_post:
        result = await provider.generate(
            VideoRequest(prompt="a drone over the valley", model="seedance-2.0-fast")
        )
    assert result.is_ok()
    assert mock_post.call_args.kwargs["json"]["model"] == "seedance-2.0-fast"


@pytest.mark.asyncio
async def test_generate_text_to_video_keeps_flags_and_seed() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=5)
    with _patch_ok_gateway() as mock_post:
        result = await provider.generate(
            VideoRequest(
                prompt="a drone over the valley",
                mode=VideoMode.TEXT_TO_VIDEO,
                generate_audio=True,
                return_last_frame=True,
                seed=42,
                ratio="9:16",
            )
        )
    assert result.is_ok()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["generate_audio"] is True
    assert payload["return_last_frame"] is True
    assert payload["seed"] == 42
    assert payload["ratio"] == "9:16"


@pytest.mark.asyncio
async def test_generate_passes_extra_flags() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=5)
    with _patch_ok_gateway() as mock_post:
        result = await provider.generate(
            VideoRequest(
                prompt="a drone over the valley",
                mode=VideoMode.MULTIMODAL_REFERENCE,
                reference_images=["https://cdn.example.com/r/1.png"],
                extra={"human_review": True, "scene_optimize": "anime style"},
            )
        )
    assert result.is_ok()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["human_review"] is True
    assert payload["scene_optimize"] == "anime style"


@pytest.mark.asyncio
async def test_generate_extra_keeps_explicit_bools_omits_empty_strings() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=5)
    with _patch_ok_gateway() as mock_post:
        result = await provider.generate(
            VideoRequest(
                prompt="a drone over the valley",
                mode=VideoMode.MULTIMODAL_REFERENCE,
                reference_images=["https://cdn.example.com/r/1.png"],
                extra={"human_review": False, "scene_optimize": "  "},
            )
        )
    assert result.is_ok()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["human_review"] is False
    assert "scene_optimize" not in payload


@pytest.mark.asyncio
async def test_generate_extra_does_not_override_core_keys() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=5)
    with _patch_ok_gateway() as mock_post:
        result = await provider.generate(
            VideoRequest(
                prompt="a drone over the valley",
                duration_seconds=4,
                mode=VideoMode.MULTIMODAL_REFERENCE,
                reference_images=["https://cdn.example.com/r/1.png"],
                extra={"duration": 99, "prompt": "override"},
            )
        )
    assert result.is_ok()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["duration"] == 4
    assert payload["prompt"] == "a drone over the valley"


@pytest.mark.asyncio
async def test_generate_submits_then_polls_until_completed() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=10)

    submit_cm = MagicMock()
    submit_cm.__aenter__ = AsyncMock(return_value=_mock_resp(200, '{"id": "vid-1"}'))
    submit_cm.__aexit__ = AsyncMock(return_value=False)

    poll_processing_cm = MagicMock()
    poll_processing_cm.__aenter__ = AsyncMock(
        return_value=_mock_resp(200, '{"status": "processing"}')
    )
    poll_processing_cm.__aexit__ = AsyncMock(return_value=False)

    poll_done_cm = MagicMock()
    poll_done_cm.__aenter__ = AsyncMock(
        return_value=_mock_resp(
            200, '{"status": "completed", "url": "https://cdn.example/v.mp4"}'
        )
    )
    poll_done_cm.__aexit__ = AsyncMock(return_value=False)

    calls = [poll_processing_cm, poll_done_cm]

    def poll_side_effect(*args: object, **kwargs: object) -> MagicMock:
        return calls.pop(0)

    with (
        patch("aiohttp.ClientSession.post", return_value=submit_cm),
        patch("aiohttp.ClientSession.get", side_effect=poll_side_effect),
    ):
        result = await provider.generate(VideoRequest(prompt="a drone over the valley"))

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.uri == "https://cdn.example/v.mp4"
    assert asset.mime_type == "video/mp4"
    assert asset.provider == "openai"


@pytest.mark.asyncio
async def test_generate_uses_configurable_base_url_and_model() -> None:
    provider = OpenAIVideoProvider(
        api_key="key",
        model="seedance-1",
        base_url="http://gateway.internal:8080",
        poll_interval=0.01,
        max_polls=5,
    )

    submit_cm = MagicMock()
    submit_cm.__aenter__ = AsyncMock(return_value=_mock_resp(200, '{"id": "vid-1"}'))
    submit_cm.__aexit__ = AsyncMock(return_value=False)

    poll_cm = MagicMock()
    poll_cm.__aenter__ = AsyncMock(
        return_value=_mock_resp(
            200, '{"status": "completed", "url": "https://cdn.example/v.mp4"}'
        )
    )
    poll_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("aiohttp.ClientSession.post", return_value=submit_cm) as mock_post,
        patch("aiohttp.ClientSession.get", return_value=poll_cm),
    ):
        await provider.generate(VideoRequest(prompt="a drone over the valley"))

    called_url = mock_post.call_args.args[0]
    assert called_url == "http://gateway.internal:8080/v1/videos"
    sent_payload = mock_post.call_args.kwargs["json"]
    assert sent_payload["model"] == "seedance-1"


@pytest.mark.asyncio
async def test_generate_returns_err_after_poll_budget_exhausted() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=2)

    submit_cm = MagicMock()
    submit_cm.__aenter__ = AsyncMock(return_value=_mock_resp(200, '{"id": "vid-1"}'))
    submit_cm.__aexit__ = AsyncMock(return_value=False)

    poll_cm = MagicMock()
    poll_cm.__aenter__ = AsyncMock(
        return_value=_mock_resp(200, '{"status": "processing"}')
    )
    poll_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("aiohttp.ClientSession.post", return_value=submit_cm),
        patch("aiohttp.ClientSession.get", return_value=poll_cm),
    ):
        result = await provider.generate(VideoRequest(prompt="a drone over the valley"))

    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoTimeoutError)


@pytest.mark.asyncio
async def test_generate_returns_err_on_submit_401() -> None:
    provider = OpenAIVideoProvider(api_key="bad", poll_interval=0.01, max_polls=2)

    submit_cm = MagicMock()
    submit_cm.__aenter__ = AsyncMock(return_value=_mock_resp(401, "unauthorized"))
    submit_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession.post", return_value=submit_cm):
        result = await provider.generate(VideoRequest(prompt="a drone over the valley"))

    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoGenerationAuthenticationError)


@pytest.mark.asyncio
async def test_generate_returns_err_on_failed_job() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=10)

    submit_cm = MagicMock()
    submit_cm.__aenter__ = AsyncMock(return_value=_mock_resp(200, '{"id": "vid-1"}'))
    submit_cm.__aexit__ = AsyncMock(return_value=False)

    poll_cm = MagicMock()
    poll_cm.__aenter__ = AsyncMock(
        return_value=_mock_resp(200, '{"status": "failed", "error": "boom"}')
    )
    poll_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("aiohttp.ClientSession.post", return_value=submit_cm),
        patch("aiohttp.ClientSession.get", return_value=poll_cm),
    ):
        result = await provider.generate(VideoRequest(prompt="a drone over the valley"))

    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoGenerationError)


@pytest.mark.asyncio
async def test_generate_first_frame_mode_sends_image_url() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=5)
    with _patch_ok_gateway() as mock_post:
        result = await provider.generate(
            VideoRequest(
                prompt="pan across",
                image_uri="https://oss.example/first.png",
                mode=VideoMode.FIRST_FRAME,
            )
        )
    assert result.is_ok()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["image_url"] == "https://oss.example/first.png"
    assert "first_frame_image" not in payload
    assert "reference_images" not in payload


@pytest.mark.asyncio
async def test_generate_first_last_frame_mode_sends_both_frames() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=5)
    with _patch_ok_gateway() as mock_post:
        result = await provider.generate(
            VideoRequest(
                prompt="transition",
                image_uri="https://oss.example/first.png",
                last_frame_image="https://oss.example/last.png",
                mode=VideoMode.FIRST_LAST_FRAME,
            )
        )
    assert result.is_ok()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["first_frame_image"] == "https://oss.example/first.png"
    assert payload["last_frame_image"] == "https://oss.example/last.png"


@pytest.mark.asyncio
async def test_generate_multimodal_mode_sends_references_and_flags() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=5)
    with _patch_ok_gateway() as mock_post:
        result = await provider.generate(
            VideoRequest(
                prompt="@图片1 保持角色",
                reference_images=["https://oss.example/r/1.png"],
                reference_videos=["https://oss.example/r/c.mp4"],
                reference_audios=["https://oss.example/r/v.wav"],
                generate_audio=True,
                return_last_frame=True,
                ratio="9:16",
                seed=42,
            )
        )
    assert result.is_ok()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["reference_images"] == ["https://oss.example/r/1.png"]
    assert payload["reference_videos"] == ["https://oss.example/r/c.mp4"]
    assert payload["reference_audios"] == ["https://oss.example/r/v.wav"]
    assert payload["generate_audio"] is True
    assert payload["return_last_frame"] is True
    assert payload["ratio"] == "9:16"
    assert payload["seed"] == 42


@pytest.mark.asyncio
async def test_generate_derives_multimodal_mode_from_references() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=5)
    with _patch_ok_gateway() as mock_post:
        result = await provider.generate(
            VideoRequest(
                prompt="keep the style",
                reference_images=["https://oss.example/r/1.png"],
                generate_audio=True,
            )
        )
    assert result.is_ok()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["reference_images"] == ["https://oss.example/r/1.png"]
    assert payload["generate_audio"] is True


@pytest.mark.asyncio
async def test_generate_derives_first_last_frame_mode_from_last_frame_image() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=5)
    with _patch_ok_gateway() as mock_post:
        result = await provider.generate(
            VideoRequest(
                prompt="transition",
                image_uri="https://oss.example/first.png",
                last_frame_image="https://oss.example/last.png",
            )
        )
    assert result.is_ok()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["first_frame_image"] == "https://oss.example/first.png"
    assert payload["last_frame_image"] == "https://oss.example/last.png"


@pytest.mark.asyncio
async def test_generate_derives_first_frame_mode_from_image_uri() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=5)
    with _patch_ok_gateway() as mock_post:
        result = await provider.generate(
            VideoRequest(prompt="pan across", image_uri="https://oss.example/first.png")
        )
    assert result.is_ok()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["image_url"] == "https://oss.example/first.png"
    assert "first_frame_image" not in payload


@pytest.mark.asyncio
async def test_generate_text_to_video_omits_reference_keys() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=5)
    with _patch_ok_gateway() as mock_post:
        result = await provider.generate(
            VideoRequest(
                prompt="a drone over the valley",
                mode=VideoMode.TEXT_TO_VIDEO,
                reference_images=["https://oss.example/r/1.png"],
            )
        )
    assert result.is_ok()
    payload = mock_post.call_args.kwargs["json"]
    assert "image_url" not in payload
    assert "reference_images" not in payload


@pytest.mark.asyncio
async def test_generate_first_last_frame_missing_last_frame_returns_err() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=5)
    with patch("aiohttp.ClientSession.post") as mock_post:
        result = await provider.generate(
            VideoRequest(
                prompt="transition",
                image_uri="https://oss.example/first.png",
                mode=VideoMode.FIRST_LAST_FRAME,
            )
        )
    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoGenerationError)
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_generate_multimodal_no_references_returns_err() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=5)
    with patch("aiohttp.ClientSession.post") as mock_post:
        result = await provider.generate(
            VideoRequest(prompt="nothing to condition on", mode=VideoMode.MULTIMODAL_REFERENCE)
        )
    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoGenerationError)
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_generate_multimodal_too_many_images_returns_err() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=5)
    with patch("aiohttp.ClientSession.post") as mock_post:
        result = await provider.generate(
            VideoRequest(
                prompt="too many",
                mode=VideoMode.MULTIMODAL_REFERENCE,
                reference_images=[f"https://oss.example/r/{i}.png" for i in range(10)],
            )
        )
    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoGenerationError)
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_generate_multimodal_too_many_videos_returns_err() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=5)
    with patch("aiohttp.ClientSession.post") as mock_post:
        result = await provider.generate(
            VideoRequest(
                prompt="too many",
                mode=VideoMode.MULTIMODAL_REFERENCE,
                reference_images=["https://oss.example/r/1.png"],
                reference_videos=[f"https://oss.example/r/v{i}.mp4" for i in range(4)],
            )
        )
    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoGenerationError)
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_generate_multimodal_too_many_audios_returns_err() -> None:
    provider = OpenAIVideoProvider(api_key="key", poll_interval=0.01, max_polls=5)
    with patch("aiohttp.ClientSession.post") as mock_post:
        result = await provider.generate(
            VideoRequest(
                prompt="too many",
                mode=VideoMode.MULTIMODAL_REFERENCE,
                reference_images=["https://oss.example/r/1.png"],
                reference_audios=[f"https://oss.example/r/a{i}.wav" for i in range(4)],
            )
        )
    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoGenerationError)
    mock_post.assert_not_called()
