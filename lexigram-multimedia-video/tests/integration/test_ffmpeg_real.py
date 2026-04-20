import shutil

import pytest

from lexigram.contracts.multimedia.types import ExtractThumbnail, MediaAsset, Trim
from lexigram.multimedia.video.config import VideoProcessingConfig
from lexigram.multimedia.video.processing.ffmpeg import FFmpegVideoProcessor

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not installed"
)


async def _make_synthetic_clip(tmp_path) -> bytes:
    import asyncio

    path = str(tmp_path / "synthetic.mp4")
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=320x240:d=2",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=stereo",
        "-shortest",
        "-t",
        "2",
        path,
    )
    await proc.wait()
    with open(path, "rb") as f:
        return f.read()


@pytest.mark.asyncio
async def test_trim_real_ffmpeg(tmp_path) -> None:
    clip_bytes = await _make_synthetic_clip(tmp_path)
    config = VideoProcessingConfig(temp_dir=str(tmp_path))
    processor = FFmpegVideoProcessor(config=config)

    asset = MediaAsset(mime_type="video/mp4", provider="test", bytes_data=clip_bytes)
    result = await processor.process(Trim(asset=asset, start=0.0, end=1.0))

    assert result.is_ok()
    assert len(result.unwrap().bytes_data) > 0


@pytest.mark.asyncio
async def test_extract_thumbnail_real_ffmpeg(tmp_path) -> None:
    clip_bytes = await _make_synthetic_clip(tmp_path)
    config = VideoProcessingConfig(temp_dir=str(tmp_path))
    processor = FFmpegVideoProcessor(config=config)

    asset = MediaAsset(mime_type="video/mp4", provider="test", bytes_data=clip_bytes)
    result = await processor.process(ExtractThumbnail(asset=asset, timestamp=0.5))

    assert result.is_ok()
    out = result.unwrap()
    assert out.mime_type == "image/png"
    assert len(out.bytes_data) > 0


@pytest.mark.asyncio
async def test_extract_frames_real_ffmpeg(tmp_path) -> None:
    clip_bytes = await _make_synthetic_clip(tmp_path)
    config = VideoProcessingConfig(temp_dir=str(tmp_path))
    processor = FFmpegVideoProcessor(config=config)
    asset = MediaAsset(mime_type="video/mp4", provider="test", bytes_data=clip_bytes)

    result = await processor.extract_frames(asset, fps=2.0)

    assert result.is_ok()
    frames = result.unwrap()
    assert len(frames) > 0
    assert all(f.mime_type == "image/png" for f in frames)
    assert frames[0].metadata["source_fps"] == 2.0


@pytest.mark.asyncio
async def test_extract_frames_at_native_rate_stamps_probed_fps(tmp_path) -> None:
    clip_bytes = await _make_synthetic_clip(tmp_path)
    config = VideoProcessingConfig(temp_dir=str(tmp_path))
    processor = FFmpegVideoProcessor(config=config)
    asset = MediaAsset(mime_type="video/mp4", provider="test", bytes_data=clip_bytes)

    result = await processor.extract_frames(asset)

    assert result.is_ok()
    frames = result.unwrap()
    assert frames[0].metadata["source_fps"] > 0


@pytest.mark.asyncio
async def test_extract_then_assemble_frames_round_trip_real_ffmpeg(tmp_path) -> None:
    clip_bytes = await _make_synthetic_clip(tmp_path)
    config = VideoProcessingConfig(temp_dir=str(tmp_path))
    processor = FFmpegVideoProcessor(config=config)
    asset = MediaAsset(mime_type="video/mp4", provider="test", bytes_data=clip_bytes)

    extracted = await processor.extract_frames(asset, fps=2.0)
    assert extracted.is_ok()
    frames = extracted.unwrap()

    assembled = await processor.assemble_frames(frames, fps=2.0)

    assert assembled.is_ok()
    out = assembled.unwrap()
    assert out.mime_type == "video/mp4"
    assert len(out.bytes_data) > 0
