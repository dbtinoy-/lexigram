"""Unit tests for scripts/compare_renderers.py metric extractors.

Uses tiny synthetic clips (libx264/testsrc — no GPU, no Kdenlive needed).
"""

import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_renderers import (  # path inserted above
    BLACK_LUM,
    PILL_RGB,
    compare_metrics,
    count_nonblack_center,
    count_pixels,
    count_white,
    faststart_present,
    ffprobe_metrics,
    frame_rgb,
    mean_luminance,
    psnr,
    silence_events,
)

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _encode(src_args: list[str], out: Path, extra: list[str] | None = None) -> Path:
    cmd = [
        "ffmpeg",
        "-y",
        *src_args,
        *((extra or []) + ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)]),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return out


def _testsrc(path: Path, duration: float = 2.0, movflags: list[str] | None = None) -> Path:
    return _encode(
        ["-f", "lavfi", "-i", "testsrc=size=320x240:rate=30", "-t", str(duration)],
        path,
        extra=movflags,
    )


def test_ffprobe_metrics_extracts_shape(tmp_path):
    clip = _testsrc(tmp_path / "a.mp4")
    m = ffprobe_metrics(clip)
    assert m["width"] == 320 and m["height"] == 240
    assert abs(m["fps"] - 30) < 0.01
    assert m["duration"] == pytest.approx(2.0, abs=0.05)
    assert m["codec"] == "h264"
    assert m["bit_rate"] > 0
    assert m["audio_duration"] is None


def test_faststart_detection(tmp_path):
    plain = _testsrc(tmp_path / "plain.mp4")
    fast = _testsrc(tmp_path / "fast.mp4", movflags=["-movflags", "+faststart"])
    assert faststart_present(plain) is False
    assert faststart_present(fast) is True


def test_silence_events_detects_tail(tmp_path):
    out = tmp_path / "tone_silence.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x120:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-filter_complex",
            "[1:a]apad[a]",
            "-map",
            "0:v",
            "-map",
            "[a]",
            "-t",
            "2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(out),
        ],
        capture_output=True,
        check=True,
    )
    events = silence_events(out)
    assert events
    assert events[0]["start"] == pytest.approx(1.0, abs=0.15)
    assert events[0]["end"] == pytest.approx(2.0, abs=0.1)


def test_mean_luminance_black_and_white(tmp_path):
    black = _encode(
        ["-f", "lavfi", "-i", "color=black:size=64x64", "-t", "1"], tmp_path / "black.mp4"
    )
    white = _encode(
        ["-f", "lavfi", "-i", "color=white:size=64x64", "-t", "1"], tmp_path / "white.mp4"
    )
    b_raw, bw, bh = frame_rgb(black, 0.3)
    w_raw, ww, wh = frame_rgb(white, 0.3)
    assert mean_luminance(b_raw, bw, bh) < 0.02
    assert mean_luminance(w_raw, ww, wh) > 0.98
    assert mean_luminance(b_raw, bw, bh) < BLACK_LUM


def test_count_pixels_finds_pill_color(tmp_path):
    out = tmp_path / "pill.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=black:size=64x64",
            "-t",
            "1",
            "-vf",
            f"drawbox=x=10:y=20:w=40:h=10:color=0x{0x7C5CFA:06x}:t=fill",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ],
        capture_output=True,
        check=True,
    )
    raw, w, h = frame_rgb(out, 0.3)
    assert count_pixels(raw, w, h, PILL_RGB, tol=12) > 0
    assert count_pixels(raw, w, h, (255, 0, 0), tol=0) == 0


def test_count_white_region_and_nonblack_center(tmp_path):
    out = tmp_path / "text.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=black:size=64x64",
            "-t",
            "1",
            "-vf",
            "drawbox=x=0:y=8:w=64:h=8:color=white:t=fill",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ],
        capture_output=True,
        check=True,
    )
    raw, w, h = frame_rgb(out, 0.3)
    assert count_white(raw, w, h, 0, 16) > 0
    assert count_white(raw, w, h, 32, 64) == 0
    assert count_nonblack_center(raw, w, h) > 0
    black = _encode(
        ["-f", "lavfi", "-i", "color=black:size=64x64", "-t", "1"], tmp_path / "black.mp4"
    )
    b_raw, bw, bh = frame_rgb(black, 0.3)
    assert count_nonblack_center(b_raw, bw, bh) == 0


def test_psnr_same_vs_different(tmp_path):
    a = _testsrc(tmp_path / "a.mp4")
    assert psnr(a, a) is not None and psnr(a, a) > 30
    black = _encode(
        ["-f", "lavfi", "-i", "color=black:size=320x240:rate=30", "-t", "1"], tmp_path / "black.mp4"
    )
    white = _encode(
        ["-f", "lavfi", "-i", "color=white:size=320x240:rate=30", "-t", "1"], tmp_path / "white.mp4"
    )
    assert psnr(black, white) is not None and psnr(black, white) < 20


def test_compare_metrics_tolerances():
    base = {
        "duration": 40.0,
        "position": 36.25,
        "expected_end_delta": 0.0,
        "width": 1080,
        "height": 1920,
        "fps": 30.0,
        "codec": "hevc",
        "bit_rate": 10_000_000,
        "faststart": True,
        "audio_start": 0.1,
        "audio_duration": 36.0,
        "tail_silent": True,
        "fade_early_lum": 0.1,
        "fade_late_lum": 0.6,
        "bg_before_lum": 0.4,
        "bg_after_lum": 0.01,
        "hook_white_px": 200,
        "highlight_pill_px": 500,
        "outro_center_px": 900,
    }
    report = compare_metrics(dict(base), dict(base))
    assert report["overall"] is True
    assert all(c["pass"] for c in report["checks"])

    drift = dict(base)
    drift["duration"] = base["duration"] + 2.0
    report = compare_metrics(dict(base), drift)
    assert report["overall"] is False
    assert next(c["metric"] for c in report["checks"] if not c["pass"]) == "duration"

    bad_shape = dict(base)
    bad_shape["expected_end_delta"] = 0.6
    report = compare_metrics(dict(base), bad_shape)
    assert report["overall"] is False

    bad_codec = dict(base)
    bad_codec["codec"] = "mpeg4"
    report = compare_metrics(dict(base), bad_codec)
    assert report["overall"] is False

    no_fade = dict(base)
    no_fade["fade_late_lum"] = no_fade["fade_early_lum"]
    report = compare_metrics(dict(base), no_fade)
    assert report["overall"] is False

    no_faststart_ffmpeg = dict(base)
    no_faststart_ffmpeg["faststart"] = False
    report = compare_metrics(dict(base), no_faststart_ffmpeg)
    assert report["overall"] is False

    no_faststart_kdenlive = dict(base)
    report = compare_metrics(no_faststart_kdenlive, dict(base))
    assert report["overall"] is True
    c = next(c for c in report["checks"] if c["metric"] == "faststart")
    assert c["pass"] is True


def test_loudness_default_negative_14():
    from shorts_creator.pipeline.render_config import RenderConfig

    assert RenderConfig().loudness_target_lufs == -14
    assert RenderConfig().audio_normalize is True


@pytest.mark.asyncio
async def test_loudnorm_remux_preserves_video_stream(tmp_path):
    src = tmp_path / "in.mp4"
    enc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc2=size=320x240:rate=10:duration=2",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=2",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-shortest",
        str(src),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await enc.wait()
    tmp = f"{src}.loudnorm.mp4"
    norm = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-c:v",
        "copy",
        "-af",
        "loudnorm=I=-14.0:TP=-1.5:LRA=11",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
        tmp,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await norm.wait()
    assert os.path.exists(tmp)
