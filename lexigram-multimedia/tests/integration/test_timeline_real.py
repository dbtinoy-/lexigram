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
    import asyncio

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
async def test_timeline_render_concat_only_real_ffmpeg(tmp_path) -> None:
    blue = await _make_synthetic_clip(tmp_path, "blue")
    red = await _make_synthetic_clip(tmp_path, "red")
    config = VideoProcessingConfig(temp_dir=str(tmp_path))
    processor = FFmpegVideoProcessor(config=config)

    timeline = Timeline()
    timeline.add_clip(
        MediaAsset(mime_type="video/mp4", provider="test", bytes_data=blue)
    )
    timeline.add_clip(
        MediaAsset(mime_type="video/mp4", provider="test", bytes_data=red)
    )

    result = await timeline.render(processor)

    assert result.is_ok()
    assert len(result.unwrap().bytes_data) > 0
