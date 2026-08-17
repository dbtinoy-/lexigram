import dataclasses
from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Ok
from lexigram.contracts.multimedia.types import (
    ComposeVideo,
    MediaAsset,
    VideoMode,
    VideoRequest,
)
from lexigram.multimedia.video.tasks import VideoGenerationTask, VideoProcessingTask


@pytest.mark.asyncio
async def test_task_calls_backend_generate_and_returns_asset_dict() -> None:
    backend = AsyncMock()
    backend.generate.return_value = Ok(
        MediaAsset(mime_type="video/mp4", provider="local-http", bytes_data=b"x")
    )
    task = VideoGenerationTask(backend=backend)

    result = await task.run(
        {
            "prompt": "a drone over the valley",
            "duration_seconds": 4.0,
            "resolution": "1280x720",
            "format": "mp4",
        }
    )

    backend.generate.assert_awaited_once()
    assert result["provider"] == "local-http"


@pytest.mark.asyncio
async def test_task_forwards_extra_to_request() -> None:
    backend = AsyncMock()
    backend.generate.return_value = Ok(
        MediaAsset(mime_type="video/mp4", provider="comfyui", bytes_data=b"x")
    )
    task = VideoGenerationTask(backend=backend)

    await task.run(
        {
            "prompt": "a drone over the valley",
            "duration_seconds": 4.0,
            "resolution": "1280x720",
            "format": "mp4",
            "extra": {"motion_bucket_id": 200},
        }
    )

    sent_request = backend.generate.await_args.args[0]
    assert sent_request.extra == {"motion_bucket_id": 200}


@pytest.mark.asyncio
async def test_run_preserves_all_video_request_fields() -> None:
    captured: list[VideoRequest] = []

    async def fake_generate(request: VideoRequest):
        captured.append(request)
        return Ok(
            MediaAsset(
                mime_type="video/mp4",
                provider="test",
                bytes_data=b"x",
                uri=None,
                metadata={},
            )
        )

    backend = AsyncMock()
    backend.generate = fake_generate
    task = VideoGenerationTask(backend=backend)

    request = VideoRequest(
        prompt="a cat",
        model="sora-2",
        mode=VideoMode.FIRST_LAST_FRAME,
        last_frame_image="frame.png",
        reference_images=["ref1.png"],
        reference_videos=["ref1.mp4"],
        reference_audios=["ref1.mp3"],
        generate_audio=True,
        return_last_frame=True,
        ratio="16:9",
        seed=42,
    )
    params = dataclasses.asdict(request)

    await task.run(params)

    assert captured[0] == request


@pytest.mark.asyncio
async def test_video_processing_task_trim() -> None:
    fake_backend = AsyncMock()
    fake_backend.process.return_value = Ok(
        MediaAsset(mime_type="video/mp4", provider="ffmpeg", bytes_data=b"out")
    )
    task = VideoProcessingTask(backend=fake_backend)

    result = await task.run(
        {
            "operation_type": "Trim",
            "asset": {
                "mime_type": "video/mp4",
                "provider": "local-http",
                "uri": "a.mp4",
            },
            "start": 1.0,
            "end": 2.0,
        }
    )

    assert result["bytes_data"] == b"out"
    fake_backend.process.assert_awaited_once()
    called_op = fake_backend.process.call_args[0][0]
    assert called_op.start == 1.0
    assert called_op.end == 2.0


@pytest.mark.asyncio
async def test_video_processing_task_compose_video_roundtrip() -> None:
    fake_backend = AsyncMock()
    fake_backend.process.return_value = Ok(
        MediaAsset(mime_type="video/mp4", provider="ffmpeg", bytes_data=b"out")
    )
    task = VideoProcessingTask(backend=fake_backend)

    result = await task.run(
        {
            "operation_type": "ComposeVideo",
            "asset": {
                "mime_type": "video/mp4",
                "provider": "local-http",
                "uri": "b.mp4",
            },
            "layers": [
                {
                    "asset": {
                        "mime_type": "video/quicktime",
                        "provider": "local-http",
                        "uri": "l.mov",
                    },
                    "start": 1.0,
                    "end": None,
                    "fade_in": 0.0,
                    "fade_out": 0.0,
                }
            ],
            "audio_layers": [],
            "fade_in": 0.0,
            "fade_out": 0.0,
            "base_fade_out": 0.75,
            "encode": {
                "codec": "hevc_nvenc",
                "bitrate": "10M",
                "resolution": "1080x1920",
                "fps": 30,
            },
        }
    )

    assert result["bytes_data"] == b"out"
    fake_backend.process.assert_awaited_once()
    called_op = fake_backend.process.call_args[0][0]
    assert isinstance(called_op, ComposeVideo)
    assert called_op.base_fade_out == 0.75
    assert called_op.layers[0].start == 1.0
    assert called_op.encode is not None and called_op.encode.codec == "hevc_nvenc"


@pytest.mark.asyncio
async def test_video_processing_task_compose_video_encode_none() -> None:
    fake_backend = AsyncMock()
    fake_backend.process.return_value = Ok(
        MediaAsset(mime_type="video/mp4", provider="ffmpeg", bytes_data=b"out")
    )
    task = VideoProcessingTask(backend=fake_backend)

    result = await task.run(
        {
            "operation_type": "ComposeVideo",
            "asset": {
                "mime_type": "video/mp4",
                "provider": "local-http",
                "uri": "b.mp4",
            },
            "layers": [],
            "audio_layers": [],
            "fade_in": 0.0,
            "fade_out": 0.0,
            "base_fade_out": 0.0,
            "encode": None,
        }
    )

    assert result["bytes_data"] == b"out"
    called_op = fake_backend.process.call_args[0][0]
    assert isinstance(called_op, ComposeVideo)
    assert called_op.encode is None
