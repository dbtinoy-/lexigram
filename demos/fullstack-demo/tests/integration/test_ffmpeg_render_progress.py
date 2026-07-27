import asyncio
import shutil

import pytest
from lexigram.contracts.multimedia.types import EncodeSpec, MediaAsset
from lexigram.multimedia.timeline import Timeline
from lexigram.multimedia.video.config import VideoProcessingConfig
from lexigram.multimedia.video.processing.ffmpeg import FFmpegVideoProcessor

from shorts_creator.pipeline.pipeline import ReelPipeline
from shorts_creator.services.render_progress import RenderProgressStore

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


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
    with open(path, "rb") as f:  # noqa: ASYNC230
        return f.read()


async def _make_overlay(tmp_path) -> bytes:
    path = tmp_path / "ov_red.mov"
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=red@0.9:size=160x120:rate=10:duration=1",
        "-c:v",
        "qtrle",
        "-pix_fmt",
        "rgba",
        str(path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    with open(path, "rb") as f:  # noqa: ASYNC230
        return f.read()


@pytest.mark.asyncio
async def test_timeline_render_streams_progress_to_store(tmp_path) -> None:
    base = await _make_base(tmp_path)
    overlay = await _make_overlay(tmp_path)

    store = RenderProgressStore()
    run_id = "fake-run"
    store.create_queue(run_id)

    async def on_stage(stage: str, progress: float, message: str) -> None:
        store.push(run_id, {"event": "progress", "data": {"stage": stage, "progress": progress}})

    pipeline = ReelPipeline(progress_callback=on_stage)
    pipeline._progress_tasks = set()
    bridge = pipeline._make_progress_bridge(asyncio.get_running_loop())

    timeline = Timeline()
    timeline.add_clip(MediaAsset(mime_type="video/mp4", provider="test", bytes_data=base))
    timeline.add_overlay(
        MediaAsset(mime_type="video/quicktime", provider="test", bytes_data=overlay),
        start=0.0,
        end=1.0,
    )
    timeline.set_fade_in(0.2).set_encode(
        EncodeSpec(codec="libx264", bitrate="200k", resolution="320x240", fps=10)
    )

    processor = FFmpegVideoProcessor(
        config=VideoProcessingConfig(temp_dir=str(tmp_path), timeout=120)
    )
    result = await timeline.render(processor, progress_callback=bridge)
    if pipeline._progress_tasks:
        await asyncio.gather(*pipeline._progress_tasks)

    assert result.is_ok()

    queue = store._queues[run_id]
    events = [queue.get_nowait() for _ in range(queue.qsize())]
    render_progress = [e["data"]["progress"] for e in events if e["data"]["stage"] == "render"]
    assert render_progress
    assert all(
        render_progress[i] <= render_progress[i + 1] for i in range(len(render_progress) - 1)
    )
    assert render_progress[-1] == 1.0
