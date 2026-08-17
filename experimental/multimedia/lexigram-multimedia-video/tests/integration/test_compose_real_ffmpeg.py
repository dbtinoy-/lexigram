import asyncio
import shutil

import pytest

from lexigram.contracts.multimedia.types import ComposeLayer, ComposeVideo, MediaAsset
from lexigram.multimedia.video.config import VideoProcessingConfig
from lexigram.multimedia.video.processing.ffmpeg import FFmpegVideoProcessor
from lexigram.multimedia.video.processing.media_io import probe_duration

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not installed"
)


async def _make_base(tmp_path) -> bytes:
    path = tmp_path / "base.mp4"
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=320x240:rate=10:duration=4",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    with open(path, "rb") as f:
        return f.read()


async def _make_overlay(tmp_path, color: str, duration: float) -> bytes:
    path = tmp_path / f"ov_{color}.mov"
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c={color}@0.9:size=160x120:rate=10:duration={duration}",
        "-c:v",
        "qtrle",
        "-pix_fmt",
        "rgba",
        str(path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    with open(path, "rb") as f:
        return f.read()


async def _mean_red_top_left(path, timestamp: float, width: int, height: int) -> float:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-ss",
        str(timestamp),
        "-i",
        str(path),
        "-frames:v",
        "1",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    raw, _ = await proc.communicate()
    quadrant_pixels = (width // 2) * (height // 2)
    assert len(raw) >= quadrant_pixels * 3
    red = sum(raw[i] for i in range(0, quadrant_pixels * 3, 3))
    return red / quadrant_pixels


@pytest.mark.asyncio
async def test_compose_real_ffmpeg_overlay_window_and_duration(tmp_path) -> None:
    base = await _make_base(tmp_path)
    overlay = await _make_overlay(tmp_path, "red", 1.0)
    config = VideoProcessingConfig(temp_dir=str(tmp_path))
    processor = FFmpegVideoProcessor(config=config)
    op = ComposeVideo(
        asset=MediaAsset(mime_type="video/mp4", provider="test", bytes_data=base),
        layers=[
            ComposeLayer(
                asset=MediaAsset(
                    mime_type="video/quicktime", provider="test", bytes_data=overlay
                ),
                start=1.0,
                end=2.0,
            )
        ],
    )
    result = await processor.process(op)
    assert result.is_ok()
    out = result.unwrap().bytes_data
    assert len(out) > 0

    out_path = tmp_path / "out.mp4"
    out_path.write_bytes(out)
    duration = await probe_duration(str(out_path))
    assert abs(duration - 4.0) < 0.5

    red_visible = await _mean_red_top_left(str(out_path), 1.5, 320, 240)
    red_absent = await _mean_red_top_left(str(out_path), 3.5, 320, 240)
    assert red_visible > 180
    assert red_visible - red_absent > 40
