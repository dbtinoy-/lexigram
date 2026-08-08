"""Render a fixture with the ffmpeg pipeline and compare two renders
(design spec §9). The kdenlive leg was removed with the kdenlive renderer.

Subcommands:
    render  --fixture F --out-dir D
        Run one headless pipeline render; writes parity_ffmpeg.mp4.
    compare --fixture F --kdenlive A.mp4 --ffmpeg B.mp4 --out O.json
        Extract metrics from two renders and write the parity report.
        Exits nonzero when any hard metric is out of tolerance.

Run from the repo root:  uv run python scripts/compare_renderers.py ...
"""

import argparse
import asyncio
import json
import re
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PILL_RGB = (124, 92, 250)
PILL_TOL = 12
CAPTION_Y0 = 850
CAPTION_Y1 = 1050
WHITE_THRESHOLD = 235
BLACK_LUM = 8 / 255
OUTRO_LEAD = 0.75
DURATION_TOL = 1.5
BITRATE_TOL = 0.25
FPS_TOL = 0.1
FADE_RATIO_TOL = 0.25
HOOK_WHITE_MIN = 50
PILL_PX_MIN = 5
OUTRO_PX_MIN = 100
OUTRO_LEAD = 0.75
OUTRO_DURATION = 3.0


def _run(cmd: list[str]) -> str:
    return subprocess.run(
        cmd, capture_output=True, text=True, check=True
    ).stdout


def ffprobe_metrics(path: str | Path) -> dict:
    """Container/stream facts for a render file."""
    out = _run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(path),
    ])
    data = json.loads(out)
    v = next(s for s in data["streams"] if s.get("codec_type") == "video")
    a = next((s for s in data["streams"] if s.get("codec_type") == "audio"), None)
    fmt = data["format"]
    num, den = v["r_frame_rate"].split("/")
    fps = float(num) / float(den)
    size = Path(path).stat().st_size
    duration = float(fmt.get("duration", 0) or 0)
    bit_rate = fmt.get("bit_rate")
    if bit_rate:
        bit_rate = int(bit_rate)
    elif duration > 0:
        bit_rate = int(size * 8 / duration)
    audio_duration = float(a["duration"]) if a and a.get("duration") else None
    return {
        "duration": duration,
        "width": v["width"],
        "height": v["height"],
        "fps": fps,
        "codec": v["codec_name"],
        "bit_rate": bit_rate,
        "audio_duration": audio_duration,
        "file_size": size,
    }


def faststart_present(path: str | Path) -> bool:
    """True when the mp4 'moov' box precedes 'mdat' (faststart)."""
    moov_pos = None
    mdat_pos = None
    with open(path, "rb") as f:
        while True:
            header = f.read(8)
            if len(header) < 8:
                break
            size, box_type = struct.unpack(">I4s", header)
            box_start = f.tell() - 8
            if size == 1:
                ext = f.read(8)
                if len(ext) < 8:
                    break
                size = struct.unpack(">Q", ext)[0]
            elif size == 0:
                size = None
            name = box_type.decode("latin1")
            if name == "moov" and moov_pos is None:
                moov_pos = box_start
            elif name == "mdat" and mdat_pos is None:
                mdat_pos = box_start
            if size is None or size < 8:
                break
            f.seek(box_start + size)
    return moov_pos is not None and (mdat_pos is None or moov_pos < mdat_pos)


def silence_events(path: str | Path, noise: str = "-25dB", min_dur: float = 0.3) -> list[dict]:
    """Silence windows from ffmpeg silencedetect (stderr parse)."""
    proc = subprocess.run(
        ["ffmpeg", "-i", str(path), "-af",
         f"silencedetect=noise={noise}:d={min_dur}", "-f", "null", "-"],
        capture_output=True, text=True, check=False,
    )
    events: list[dict] = []
    start = None
    for line in proc.stderr.splitlines():
        m = re.search(r"silence_start: ([\d.]+)", line)
        if m:
            start = float(m.group(1))
            continue
        m = re.search(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", line)
        if m and start is not None:
            events.append({"start": start, "end": float(m.group(1)),
                           "duration": float(m.group(2))})
    return events


def frame_rgb(path: str | Path, t: float) -> tuple[bytes, int, int]:
    """Decode one frame at time t (precise seek) into rgb24 bytes."""
    probe = ffprobe_metrics(path)
    duration = probe["duration"]
    t = max(0.0, min(t, max(duration - 0.05, 0.0)))
    raw = subprocess.run(
        ["ffmpeg", "-i", str(path), "-ss", str(t), "-frames:v", "1",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True,
    ).stdout
    if len(raw) < probe["width"] * probe["height"] * 3:
        return bytes(probe["width"] * probe["height"] * 3), probe["width"], probe["height"]
    return raw, probe["width"], probe["height"]


def mean_luminance(raw: bytes, w: int, h: int) -> float:
    """Mean RGB luminance scaled to 0..1."""
    n = w * h
    if n == 0 or len(raw) < n * 3:
        return 0.0
    total = sum(raw[i * 3] for i in range(n))
    return total / (n * 255)


def count_pixels(raw: bytes, w: int, h: int, rgb: tuple[int, int, int],
                 tol: int = 0, x0: int = 0, x1: int | None = None,
                 y0: int = 0, y1: int | None = None) -> int:
    """Count pixels within tol of rgb in a region (default: full frame)."""
    x1 = x1 if x1 is not None else w
    y1 = y1 if y1 is not None else h
    count = 0
    for y in range(y0, min(y1, h)):
        row = y * w * 3
        for x in range(x0, min(x1, w)):
            i = row + x * 3
            if (abs(raw[i] - rgb[0]) <= tol and abs(raw[i + 1] - rgb[1]) <= tol
                    and abs(raw[i + 2] - rgb[2]) <= tol):
                count += 1
    return count


def count_white(raw: bytes, w: int, h: int, y0: int, y1: int,
                threshold: int = WHITE_THRESHOLD) -> int:
    """Count near-white pixels in a horizontal band (caption text)."""
    count = 0
    for y in range(max(y0, 0), min(y1, h)):
        row = y * w * 3
        for x in range(w):
            i = row + x * 3
            if raw[i] >= threshold and raw[i + 1] >= threshold and raw[i + 2] >= threshold:
                count += 1
    return count


def count_nonblack_center(raw: bytes, w: int, h: int,
                          threshold: int = 16, margin: float = 0.2) -> int:
    """Count pixels brighter than threshold in the center region (outro check)."""
    x0, x1 = int(w * margin), int(w * (1 - margin))
    y0, y1 = int(h * margin), int(h * (1 - margin))
    count = 0
    for y in range(y0, y1):
        row = y * w * 3
        for x in range(x0, x1):
            i = row + x * 3
            if max(raw[i], raw[i + 1], raw[i + 2]) >= threshold:
                count += 1
    return count


def psnr(path_a: str | Path, path_b: str | Path) -> float | None:
    """Global PSNR between two files (soft signal)."""
    proc = subprocess.run(
        ["ffmpeg", "-i", str(path_a), "-i", str(path_b), "-lavfi", "psnr",
         "-f", "null", "-"],
        capture_output=True, text=True, check=False,
    )
    for line in proc.stderr.splitlines():
        m = re.search(r"average:(inf|[\d.]+)", line)
        if m:
            return float(m.group(1)) if m.group(1) != "inf" else float("inf")
    return None


def render_metrics(path: str | Path) -> dict:
    """All §9.1 semantic metrics for one render file.

    Narration end (position) is derived from the trailing silence window
    (silencedetect), because the kdenlive render pads its audio stream to
    the full project length while the ffmpeg render ends the audio at the
    narration.
    """
    probe = ffprobe_metrics(path)
    sils = silence_events(path)
    audio_start = sils[0]["end"] if (sils and sils[0]["start"] < 0.2) else 0.0
    d = probe["duration"]
    audio_end = probe["audio_duration"] or d
    trailing = None
    for s in sils:
        if s["end"] >= audio_end - 0.25:
            trailing = s
    position = trailing["start"] if trailing else audio_end
    outro_start = position + OUTRO_LEAD
    expected_end = position + OUTRO_LEAD + OUTRO_DURATION
    # ffmpeg ends the audio stream at the narration; kdenlive pads it with
    # silence to the project end. Both mean: no narration in the outro tail.
    tail_silent = (audio_end + 0.5 <= d) or (trailing is not None and trailing["duration"] >= 1.0)

    def _lum(t: float) -> float:
        raw, w, h = frame_rgb(path, max(0.0, min(t, max(d - 0.05, 0.0))))
        return mean_luminance(raw, w, h)

    fade_early, fade_late = _lum(0.25), _lum(0.6)
    bg_before, bg_after = _lum(position - 0.4), _lum(position + 0.1)

    hook_raw, hook_w, hook_h = frame_rgb(path, 1.0)
    hook_white = count_white(hook_raw, hook_w, hook_h, CAPTION_Y0, CAPTION_Y1)

    highlight_max = 0
    for frac in (0.30, 0.45, 0.60):
        raw, w, h = frame_rgb(path, d * frac)
        highlight_max = max(
            highlight_max,
            count_pixels(raw, w, h, PILL_RGB, PILL_TOL, y0=CAPTION_Y0, y1=CAPTION_Y1),
        )

    outro_raw, outro_w, outro_h = frame_rgb(path, outro_start + 0.5)
    outro_center = count_nonblack_center(outro_raw, outro_w, outro_h)

    return {
        "duration": d,
        "position": position,
        "expected_end_delta": abs(d - expected_end),
        "width": probe["width"],
        "height": probe["height"],
        "fps": probe["fps"],
        "codec": probe["codec"],
        "bit_rate": probe["bit_rate"],
        "faststart": faststart_present(path),
        "audio_start": audio_start,
        "audio_duration": probe["audio_duration"],
        "tail_silent": tail_silent,
        "fade_early_lum": fade_early,
        "fade_late_lum": fade_late,
        "bg_before_lum": bg_before,
        "bg_after_lum": bg_after,
        "hook_white_px": hook_white,
        "highlight_pill_px": highlight_max,
        "outro_center_px": outro_center,
    }


def _tolerance(name: str) -> str:
    return {
        "duration": f"+/-{DURATION_TOL:.1f}s (TTS nondeterminism)",
        "timeline_shape": "video end == narration end + 3.75s",
        "resolution": "exact",
        "fps": f"+/-{FPS_TOL}",
        "codec": "hevc both",
        "bit_rate": f"+/-{BITRATE_TOL * 100:.0f}%",
        "faststart": "ffmpeg only",
        "audio_start": "< 0.5s",
        "tail_silent": "trailing silence covers outro tail",
        "fade_in": "increases, ratio within 25%",
        "bg_fade_out": "black in outro window",
        "hook_visible": f">= {HOOK_WHITE_MIN} white px",
        "highlight": f">= {PILL_PX_MIN} pill px",
        "outro_visible": f">= {OUTRO_PX_MIN} center px",
    }[name]


def compare_metrics(k: dict, f: dict) -> dict:
    """Compare two render_metrics dicts; returns the parity report."""
    checks: list[dict] = []

    def _add(name: str, passed: bool, detail: str, kv=None, fv=None) -> None:
        checks.append({"metric": name, "tolerance": _tolerance(name),
                       "pass": bool(passed),
                       "kdenlive": kv if kv is not None else k.get(name),
                       "ffmpeg": fv if fv is not None else f.get(name),
                       "detail": detail})

    _add("duration", abs(k["duration"] - f["duration"]) <= DURATION_TOL,
         f"|{k['duration']:.3f} - {f['duration']:.3f}|s (TTS nondeterminism)",
         kv=f"{k['duration']:.3f}s", fv=f"{f['duration']:.3f}s")
    _add("timeline_shape",
         k["expected_end_delta"] <= 0.25 and f["expected_end_delta"] <= 0.25,
         f"video end vs position+outro window: k={k['expected_end_delta']:.3f}s "
         f"f={f['expected_end_delta']:.3f}s",
         kv=f"{k['position']:.2f}+3.75s", fv=f"{f['position']:.2f}+3.75s")
    _add("resolution",
         k["width"] == 1080 and k["height"] == 1920
         and f["width"] == 1080 and f["height"] == 1920,
         f"k={k['width']}x{k['height']} f={f['width']}x{f['height']}",
         kv=f"{k['width']}x{k['height']}", fv=f"{f['width']}x{f['height']}")
    _add("fps", abs(k["fps"] - 30) <= FPS_TOL and abs(f["fps"] - 30) <= FPS_TOL,
         f"k={k['fps']:.3f} f={f['fps']:.3f}")
    _add("codec", k["codec"] in ("hevc", "h265") and f["codec"] in ("hevc", "h265"),
         f"k={k['codec']} f={f['codec']}")
    br_ok = True
    br_detail = f"k={k['bit_rate']} f={f['bit_rate']}"
    if k["bit_rate"] and f["bit_rate"]:
        lo, hi = min(k["bit_rate"], f["bit_rate"]), max(k["bit_rate"], f["bit_rate"])
        br_ok = (hi - lo) / lo <= BITRATE_TOL
    _add("bit_rate", br_ok, br_detail)
    # kdenlive's MLT preset never writes faststart; gate only the ffmpeg side.
    _add("faststart", bool(f["faststart"]),
         f"k={k['faststart']} (kdenlive preset lacks faststart; not gated) "
         f"f={f['faststart']}")
    _add("audio_start", k["audio_start"] < 0.5 and f["audio_start"] < 0.5,
         f"k={k['audio_start']:.3f}s f={f['audio_start']:.3f}s")
    _add("tail_silent", bool(k["tail_silent"]) and bool(f["tail_silent"]),
         f"k={k['tail_silent']} f={f['tail_silent']} (trailing silence covers outro tail)")
    k_fade = k["fade_late_lum"] > k["fade_early_lum"] and k["fade_early_lum"] > 0
    f_fade = f["fade_late_lum"] > f["fade_early_lum"] and f["fade_early_lum"] > 0
    ratio = 0.0
    if k_fade and f_fade:
        kr = k["fade_late_lum"] / k["fade_early_lum"]
        fr = f["fade_late_lum"] / f["fade_early_lum"]
        ratio = abs(kr - fr) / kr
    _add("fade_in", k_fade and f_fade and ratio <= FADE_RATIO_TOL,
         f"k {k['fade_early_lum']:.3f}->{k['fade_late_lum']:.3f} "
         f"f {f['fade_early_lum']:.3f}->{f['fade_late_lum']:.3f} ratio_drift={ratio:.2f}",
         kv=f"{k['fade_early_lum']:.3f}->{k['fade_late_lum']:.3f}",
         fv=f"{f['fade_early_lum']:.3f}->{f['fade_late_lum']:.3f}")
    bg_ok = (f["bg_before_lum"] > f["bg_after_lum"] and f["bg_after_lum"] < BLACK_LUM)
    _add("bg_fade_out", bg_ok,
         f"k {k['bg_before_lum']:.3f}->{k['bg_after_lum']:.3f} "
         f"f {f['bg_before_lum']:.3f}->{f['bg_after_lum']:.3f} "
         f"(kdenlive keeps the bg gradient in the outro lead-in; not gated)",
         kv=f"{k['bg_before_lum']:.3f}->{k['bg_after_lum']:.3f}",
         fv=f"{f['bg_before_lum']:.3f}->{f['bg_after_lum']:.3f}")
    _add("hook_visible", k["hook_white_px"] >= HOOK_WHITE_MIN
         and f["hook_white_px"] >= HOOK_WHITE_MIN,
         f"k={k['hook_white_px']} f={f['hook_white_px']} white px",
         kv=str(k["hook_white_px"]), fv=str(f["hook_white_px"]))
    _add("highlight", k["highlight_pill_px"] >= PILL_PX_MIN and f["highlight_pill_px"] >= PILL_PX_MIN,
         f"k={k['highlight_pill_px']} f={f['highlight_pill_px']} pill px",
         kv=str(k["highlight_pill_px"]), fv=str(f["highlight_pill_px"]))
    _add("outro_visible", k["outro_center_px"] >= OUTRO_PX_MIN and f["outro_center_px"] >= OUTRO_PX_MIN,
         f"k={k['outro_center_px']} f={f['outro_center_px']} center px",
         kv=str(k["outro_center_px"]), fv=str(f["outro_center_px"]))

    passed = all(c["pass"] for c in checks)
    return {"overall": bool(passed), "checks": checks}


def render_one(fixture: str, out_dir: str) -> tuple[bool, str]:
    """Headless pipeline render of the fixture (ffmpeg renderer)."""
    saved = json.loads(Path(fixture).read_text())
    from shorts_creator.pipeline.pipeline import ReelPipeline
    from shorts_creator.pipeline.script_parser import to_pipeline_script

    script = to_pipeline_script(saved)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    output = str(out / "parity_ffmpeg.mp4")
    run_dir = out / "run_ffmpeg"
    run_dir.mkdir(exist_ok=True)

    async def _main() -> bool:
        pipeline = ReelPipeline(topic=script.title, output=output,
                                render_timeout=900)
        pipeline.script = script
        pipeline.run_dir = str(run_dir)
        return await pipeline.run()

    ok = asyncio.run(_main())
    return ok, output


def _write_report(report: dict, out_path: Path) -> None:
    report["generated_at"] = datetime.now(timezone.utc).isoformat()  # noqa: UP017  # datetime.UTC missing in this runtime
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    lines = [
        f"# Parity report: ffmpeg vs kdenlive ({report['generated_at']})",
        "",
        f"Fixture: `{report.get('fixture')}`  ",
        f"Overall: **{'PASS' if report['overall'] else 'FAIL'}**",
        "",
        "| Metric | Tolerance | kdenlive | ffmpeg | Pass |",
        "|---|---|---|---|---|",
    ]
    for c in report["checks"]:
        lines.append(
            f"| {c['metric']} | {c['tolerance']} | {c.get('kdenlive')} | "
            f"{c.get('ffmpeg')} | {'✅' if c['pass'] else '❌'} |"
        )
    psnr_val = report.get("psnr")
    if psnr_val is not None:
        lines.append(f"\nPSNR (soft signal): {psnr_val:.2f} dB")
    out_path.with_suffix(".md").write_text("\n".join(lines) + "\n")


def cmd_render(args: argparse.Namespace) -> int:
    ok, output = render_one(args.fixture, args.out_dir)
    print(json.dumps({"ok": ok, "output": output}))
    return 0 if ok else 1


def cmd_compare(args: argparse.Namespace) -> int:
    k = render_metrics(args.kdenlive)
    f = render_metrics(args.ffmpeg)
    report = {
        "fixture": args.fixture,
        "kdenlive_path": args.kdenlive,
        "ffmpeg_path": args.ffmpeg,
        "psnr": psnr(args.kdenlive, args.ffmpeg),
    }
    report.update(compare_metrics(k, f))
    _write_report(report, Path(args.out))
    print(json.dumps({"overall": report["overall"],
                      "failed": [c["metric"] for c in report["checks"] if not c["pass"]]}))
    return 0 if report["overall"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    p_render = sub.add_parser("render", help="run one headless ffmpeg render")
    p_render.add_argument("--fixture", required=True)
    p_render.add_argument("--out-dir", required=True)
    p_render.set_defaults(func=cmd_render)

    p_compare = sub.add_parser("compare", help="compare two renders")
    p_compare.add_argument("--fixture", required=True)
    p_compare.add_argument("--kdenlive", required=True)
    p_compare.add_argument("--ffmpeg", required=True)
    p_compare.add_argument("--out", required=True)
    p_compare.set_defaults(func=cmd_compare)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
