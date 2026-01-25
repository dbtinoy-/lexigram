import asyncio
import shutil

import pytest

from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.timeline import Timeline
from lexigram.multimedia.video.config import VideoProcessingConfig
from lexigram.multimedia.video.processing.ffmpeg import FFmpegVideoProcessor

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not installed"
)


async def _make_synthetic_clip(tmp_path, color: str) -> bytes:
    path = str(tmp_path / f"{color}.mp4")
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c={color}:s=320x240:d=1",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=stereo",
        "-shortest",
        "-t",
        "1",
        path,
    )
    await proc.wait()
    with open(path, "rb") as f:
        return f.read()


@pytest.mark.asyncio
async def test_timeline_render_with_overlay_and_fade_real_ffmpeg(tmp_path) -> None:
    base = await _make_synthetic_clip(tmp_path, "blue")
    overlay = await _make_synthetic_clip(tmp_path, "red")
    config = VideoProcessingConfig(temp_dir=str(tmp_path))
    processor = FFmpegVideoProcessor(config=config)

    timeline = (
        Timeline()
        .add_clip(
            MediaAsset(mime_type="video/mp4", provider="test", bytes_data=base)
        )
        .add_overlay(
            MediaAsset(mime_type="video/mp4", provider="test", bytes_data=overlay),
            start=0.0,
            end=0.5,
        )
        .set_fade_out(0.25)
    )

    result = await timeline.render(processor)

    assert result.is_ok()
    assert len(result.unwrap().bytes_data) > 0
