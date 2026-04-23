from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Err, Ok
from lexigram.contracts.multimedia.exceptions import (
    UpscaleError,
    VideoGenerationError,
)
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.upscale.video_upscale_service import VideoUpscaleService


def _video_asset() -> MediaAsset:
    return MediaAsset(mime_type="video/mp4", provider="test", bytes_data=b"video")


def _frame(tag: str, fps: float = 24.0) -> MediaAsset:
    return MediaAsset(
        mime_type="image/png",
        provider="ffmpeg",
        bytes_data=tag.encode(),
        metadata={"source_fps": fps},
    )


@pytest.mark.asyncio
async def test_upscale_video_extracts_upscales_each_and_assembles() -> None:
    upscale_provider = AsyncMock()
    upscale_provider.upscale.side_effect = [
        Ok(_frame("up-a")),
        Ok(_frame("up-b")),
    ]
    video_processor = AsyncMock()
    video_processor.extract_frames.return_value = Ok(
        [_frame("a", fps=24.0), _frame("b", fps=24.0)]
    )
    video_processor.assemble_frames.return_value = Ok(_video_asset())

    service = VideoUpscaleService(
        upscale_provider=upscale_provider, video_processor=video_processor
    )

    result = await service.upscale_video(_video_asset(), scale_factor=4)

    assert result.is_ok()
    video_processor.extract_frames.assert_awaited_once_with(_video_asset())
    assert upscale_provider.upscale.await_count == 2
    video_processor.assemble_frames.assert_awaited_once()
    call_args = video_processor.assemble_frames.await_args
    assert call_args.kwargs["fps"] == 24.0


@pytest.mark.asyncio
async def test_upscale_video_short_circuits_on_extract_error() -> None:
    upscale_provider = AsyncMock()
    video_processor = AsyncMock()
    video_processor.extract_frames.return_value = Err(
        VideoGenerationError("extraction failed")
    )

    service = VideoUpscaleService(
        upscale_provider=upscale_provider, video_processor=video_processor
    )

    result = await service.upscale_video(_video_asset())

    assert result.is_err()
    upscale_provider.upscale.assert_not_awaited()
    video_processor.assemble_frames.assert_not_awaited()


@pytest.mark.asyncio
async def test_upscale_video_short_circuits_on_per_frame_upscale_error() -> None:
    upscale_provider = AsyncMock()
    upscale_provider.upscale.side_effect = [Err(UpscaleError("model failed"))]
    video_processor = AsyncMock()
    video_processor.extract_frames.return_value = Ok([_frame("a"), _frame("b")])

    service = VideoUpscaleService(
        upscale_provider=upscale_provider, video_processor=video_processor
    )

    result = await service.upscale_video(_video_asset())

    assert result.is_err()
    assert upscale_provider.upscale.await_count == 1
    video_processor.assemble_frames.assert_not_awaited()
