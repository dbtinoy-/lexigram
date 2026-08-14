from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Err, Ok
from lexigram.contracts.multimedia.exceptions import (
    MultimediaError,
    VideoGenerationError,
)
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.interpolate.video_interpolation_service import (
    VideoInterpolationService,
)


def _video_asset() -> MediaAsset:
    return MediaAsset(mime_type="video/mp4", provider="test", bytes_data=b"video")


def _frame(tag: str) -> MediaAsset:
    return MediaAsset(mime_type="image/png", provider="ffmpeg", bytes_data=tag.encode())


@pytest.mark.asyncio
async def test_interpolate_video_factor_2_calls_once_per_pair_and_interleaves() -> None:
    interpolation_provider = AsyncMock()
    interpolation_provider.interpolate.side_effect = [
        Ok(_frame("mid01")),
        Ok(_frame("mid12")),
    ]
    video_processor = AsyncMock()
    video_processor.extract_frames.return_value = Ok(
        [_frame("f0"), _frame("f1"), _frame("f2")]
    )
    video_processor.assemble_frames.return_value = Ok(_video_asset())

    service = VideoInterpolationService(
        interpolation_provider=interpolation_provider, video_processor=video_processor
    )

    result = await service.interpolate_video(_video_asset(), factor=2, fps=24.0)

    assert result.is_ok()
    assert interpolation_provider.interpolate.await_count == 2
    video_processor.assemble_frames.assert_awaited_once()
    assembled_frames, kwargs = (
        video_processor.assemble_frames.await_args.args[0],
        video_processor.assemble_frames.await_args.kwargs,
    )
    assert [f.bytes_data for f in assembled_frames] == [
        b"f0",
        b"mid01",
        b"f1",
        b"mid12",
        b"f2",
    ]
    assert kwargs["fps"] == 48.0


@pytest.mark.asyncio
async def test_interpolate_video_factor_4_runs_two_doubling_passes() -> None:
    interpolation_provider = AsyncMock()
    interpolation_provider.interpolate.side_effect = [
        Ok(_frame("mid01")),
        Ok(_frame("pass2-a")),
        Ok(_frame("pass2-b")),
    ]
    video_processor = AsyncMock()
    video_processor.extract_frames.return_value = Ok([_frame("f0"), _frame("f1")])
    video_processor.assemble_frames.return_value = Ok(_video_asset())

    service = VideoInterpolationService(
        interpolation_provider=interpolation_provider, video_processor=video_processor
    )

    result = await service.interpolate_video(_video_asset(), factor=4, fps=24.0)

    assert result.is_ok()
    assert interpolation_provider.interpolate.await_count == 3
    kwargs = video_processor.assemble_frames.await_args.kwargs
    assert kwargs["fps"] == 96.0


@pytest.mark.asyncio
async def test_interpolate_video_short_circuits_on_extract_error() -> None:
    interpolation_provider = AsyncMock()
    video_processor = AsyncMock()
    video_processor.extract_frames.return_value = Err(
        VideoGenerationError("extraction failed")
    )

    service = VideoInterpolationService(
        interpolation_provider=interpolation_provider, video_processor=video_processor
    )

    result = await service.interpolate_video(_video_asset(), fps=24.0)

    assert result.is_err()
    interpolation_provider.interpolate.assert_not_awaited()
    video_processor.assemble_frames.assert_not_awaited()


@pytest.mark.asyncio
async def test_interpolate_video_short_circuits_on_interpolate_error() -> None:
    interpolation_provider = AsyncMock()
    interpolation_provider.interpolate.side_effect = [
        Err(MultimediaError("model failed"))
    ]
    video_processor = AsyncMock()
    video_processor.extract_frames.return_value = Ok([_frame("f0"), _frame("f1")])

    service = VideoInterpolationService(
        interpolation_provider=interpolation_provider, video_processor=video_processor
    )

    result = await service.interpolate_video(_video_asset(), fps=24.0)

    assert result.is_err()
    video_processor.assemble_frames.assert_not_awaited()


@pytest.mark.asyncio
async def test_interpolate_video_returns_err_on_empty_frame_list() -> None:
    interpolation_provider = AsyncMock()
    video_processor = AsyncMock()
    video_processor.extract_frames.return_value = Ok([])

    service = VideoInterpolationService(
        interpolation_provider=interpolation_provider, video_processor=video_processor
    )

    result = await service.interpolate_video(_video_asset(), fps=24.0)

    assert result.is_err()
    interpolation_provider.interpolate.assert_not_awaited()
    video_processor.assemble_frames.assert_not_awaited()
