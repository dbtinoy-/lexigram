import os
import shutil
import subprocess
import sys

import pytest

from shorts_creator.models.run import Run, RunStatus
from shorts_creator.pipeline import subprocess_guard
from shorts_creator.services.module import _fail_stale_rendering_runs
from shorts_creator.services.render_progress import RenderProgressStore


class _FakeRunService:
    def __init__(self, runs):
        self.runs = list(runs)
        self.failed = []

    async def list_recent(self, limit=50):
        return self.runs

    async def list_status(self, status, limit=10_000):
        return [r for r in self.runs if r.status == status]

    async def mark_failed(self, run_id, error):
        self.failed.append((run_id, error))


def _run(status=RunStatus.RENDERING):
    return Run(project_id="p", status=status)


async def test_startup_sweep_fails_only_stale_rendering_runs():
    svc = _FakeRunService(
        [
            _run(RunStatus.RENDERING),
            _run(RunStatus.COMPLETED),
            _run(RunStatus.RENDERING),
        ]
    )
    await _fail_stale_rendering_runs(svc)
    assert len(svc.failed) == 2
    assert all(err == "Interrupted by server restart" for _, err in svc.failed)


async def test_startup_sweep_marks_recent_only():
    recent = [_run(RunStatus.RENDERING)]
    svc = _FakeRunService(recent)
    await _fail_stale_rendering_runs(svc)
    assert [run_id for run_id, _ in svc.failed] == [recent[0].id]


def test_progress_store_tracks_stage_elapsed():
    store = RenderProgressStore(keep_alive=15)
    store.create_queue("r1")
    assert store.last_activity("r1") is not None
    assert store.stage_elapsed("r1") is None

    store.push("r1", {"event": "progress", "data": {"stage": "timeline", "progress": 0.0}})
    first = store.stage_elapsed("r1")
    assert first is not None

    store.push("r1", {"event": "progress", "data": {"stage": "timeline", "progress": 0.5}})
    assert 0 <= store.stage_elapsed("r1") - first < 0.1

    store.push("r1", {"event": "progress", "data": {"stage": "render", "progress": 0.1}})
    assert store.stage_elapsed("r1") is not None
    assert store.stage_elapsed("r1") < 1.0


def test_progress_store_terminal_event_clears_tracking():
    store = RenderProgressStore(keep_alive=15)
    store.create_queue("r1")
    store.push("r1", {"event": "progress", "data": {"stage": "render", "progress": 1.0}})
    store.push("r1", {"event": "complete", "data": {}})
    store._queues["r1"].get_nowait()
    store._queues["r1"].get_nowait()
    store._queues.pop("r1", None)
    store._last_activity.pop("r1", None)
    store._stage_started.pop("r1", None)
    assert store.last_activity("r1") is None
    assert store.stage_elapsed("r1") is None


def test_run_blocking_success():
    result = subprocess_guard.run_blocking(
        [sys.executable, "-c", "print('ok')"],
        timeout=30,
        label="test echo",
    )
    assert result.returncode == 0


def test_run_blocking_failure_surfaces_stderr_tail():
    with pytest.raises(RuntimeError, match="boom"):
        subprocess_guard.run_blocking(
            [sys.executable, "-c", "import sys; sys.stderr.write('boom\\n'); sys.exit(2)"],
            timeout=30,
            label="test child",
        )
    assert not subprocess_guard._ACTIVE


def test_run_blocking_timeout_kills_child_and_unregisters():
    with pytest.raises(RuntimeError, match="timed out"):
        subprocess_guard.run_blocking(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            timeout=1,
            label="test sleeper",
        )
    assert not subprocess_guard._ACTIVE


def test_kill_all_is_scoped_by_owner():
    proc_a = subprocess_guard.spawn(
        [sys.executable, "-c", "import time; time.sleep(30)"], owner="run-a"
    )
    proc_b = subprocess_guard.spawn(
        [sys.executable, "-c", "import time; time.sleep(30)"], owner="run-b"
    )
    try:
        assert subprocess_guard.active_procs("run-a") == {proc_a}
        assert subprocess_guard.active_procs("run-b") == {proc_b}
        killed = subprocess_guard.kill_all(owner="run-a")
        assert killed >= 1
        assert not subprocess_guard.active_procs("run-a")
        assert subprocess_guard.active_procs("run-b") == {proc_b}
    finally:
        subprocess_guard.kill_all()


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_background_zoompan_reencode_yields_even_dimensions(tmp_path):
    from shorts_creator.pipeline.pipeline import _background_motion_vf

    src = str(tmp_path / "src.mp4")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=duration=2:size=320x240:rate=30",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            src,
        ],
        capture_output=True,
        check=True,
        timeout=120,
    )
    out = str(tmp_path / "motion.mp4")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            src,
            "-vf",
            _background_motion_vf("zoom", 30.0, 320, 240),
            "-an",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            out,
        ],
        capture_output=True,
        check=True,
        timeout=120,
    )
    assert os.path.exists(out)
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,duration",
            "-of",
            "csv=p=0",
            out,
        ],
        capture_output=True,
        check=True,
        text=True,
        timeout=120,
    )
    width, height, duration = probe.stdout.strip().split(",")
    assert int(width) % 2 == 0 and int(height) % 2 == 0
    assert float(duration) > 0
