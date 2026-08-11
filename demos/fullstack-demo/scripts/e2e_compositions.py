"""E2E composition matrix harness (plan Task 12).

Reads data/e2e_matrix.yaml and drives every combo against the live app:
apply the combo's compose spec via POST /api/projects/{id}/compose, start a
render via POST /api/render/start, follow the run's SSE stream
(/api/render/progress/{run_id}) until it terminates, then assert the produced
file with ffprobe (video stream, duration > 0, audio stream present) and with
ffmpeg volumedetect (mean volume within +-3 dB of the combo's
loudness_target_lufs when one is set).

Exit status is nonzero when any combo fails; a missing ffprobe/ffmpeg skips
the media assertions with a warning instead of failing.

Run from the repo root:  rtk python scripts/e2e_compositions.py --help
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import httpx
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = REPO_ROOT / "data" / "e2e_matrix.yaml"
DEFAULT_URL = "http://127.0.0.1:18080"
CONTAINER_ROOT = "/app/project/shorts-creator/"
LOUDNESS_TOL_DB = 3.0


def load_matrix(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    try:
        project = data["project"]
        ideas = data["ideas"]
        timeout_s = float(data["timeout_s"])
        combos = data["combos"]
    except (KeyError, TypeError, ValueError):
        sys.exit(f"matrix {path}: expected project, ideas, timeout_s, combos")
    if not project or not isinstance(ideas, list) or not ideas:
        sys.exit(f"matrix {path}: project and a non-empty ideas list are required")
    if timeout_s <= 0:
        sys.exit(f"matrix {path}: timeout_s must be positive")
    for combo in combos:
        if not combo.get("name") or not isinstance(combo.get("compose"), dict):
            sys.exit(f"matrix {path}: each combo needs name and compose")
        if not isinstance(combo.get("idea_index"), int):
            sys.exit(f"matrix {path}: combo {combo.get('name')!r} needs idea_index")
    return data


def select_combos(matrix: dict, raw: str) -> list[dict]:
    combos = matrix["combos"]
    if not raw:
        return combos
    wanted = [w.strip() for w in raw.split(",") if w.strip()]
    by_name = {c["name"]: c for c in combos}
    missing = [w for w in wanted if w not in by_name]
    if missing:
        sys.exit(f"unknown combo(s): {', '.join(missing)}")
    return [by_name[w] for w in wanted]


def make_client(base_url: str, token: str, params: dict | None) -> httpx.Client:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.Client(
        base_url=base_url,
        headers=headers,
        params=params,
        timeout=httpx.Timeout(30.0),
    )


def apply_compose(client: httpx.Client, project_id: str, compose: dict) -> tuple[bool, str]:
    if not compose:
        return True, ""
    try:
        resp = client.post(f"/api/projects/{project_id}/compose", json=compose)
    except httpx.HTTPError as exc:
        return False, f"compose request: {exc}"
    if resp.status_code != 200 or "Composer settings saved" not in resp.text:
        return False, f"compose rejected: HTTP {resp.status_code} {resp.text[:160]!r}"
    return True, ""


def start_render(client: httpx.Client, project_id: str, idea_index: int) -> tuple[str, str]:
    try:
        resp = client.post(
            "/api/render/start", json={"project_id": project_id, "idea_index": idea_index}
        )
    except httpx.HTTPError as exc:
        return "", f"start request: {exc}"
    if resp.status_code != 200:
        return "", f"start rejected: HTTP {resp.status_code}"
    match = re.search(r"/api/render/progress/([A-Za-z0-9_-]+)", resp.text)
    if not match:
        return "", f"no run id in start response: {resp.text[:160]!r}"
    return match.group(1), ""


def wait_terminal(client: httpx.Client, run_id: str, deadline: float) -> dict | None:
    """Follow the run's SSE stream until a terminal event or the deadline."""
    while time.monotonic() < deadline:
        event_name = None
        data_parts: list[str] = []
        stream_timeout = httpx.Timeout(connect=10.0, read=45.0, write=10.0, pool=10.0)
        try:
            with client.stream(
                "GET", f"/api/render/progress/{run_id}", timeout=stream_timeout
            ) as resp:
                for line in resp.iter_lines():
                    if not line:
                        if event_name in ("complete", "failed", "cancelled"):
                            try:
                                data = json.loads("".join(data_parts) or "{}")
                            except json.JSONDecodeError:
                                data = {}
                            return {"event": event_name, "data": data}
                        event_name = None
                        data_parts = []
                        continue
                    if line.startswith("event: "):
                        event_name = line[len("event: ") :]
                    elif line.startswith("data: "):
                        data_parts.append(line[len("data: ") :])
        except httpx.HTTPError:
            pass
        time.sleep(2.0)
    return None


def cancel_run(client: httpx.Client, run_id: str) -> None:
    try:
        client.post(f"/api/render/cancel/{run_id}")
    except httpx.HTTPError:
        pass


def local_output_path(output: str) -> Path:
    if output.startswith(CONTAINER_ROOT):
        return REPO_ROOT / output[len(CONTAINER_ROOT) :]
    path = Path(output)
    if path.is_absolute() or path.exists():
        return path
    return REPO_ROOT / "data" / "renders" / path.name


def _run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def probe_media(path: Path) -> dict:
    out = _run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]
    )
    data = json.loads(out)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = float(data["format"].get("duration", 0) or 0)
    return {"video": video is not None, "audio": audio is not None, "duration": duration}


def mean_volume_db(path: Path) -> float | None:
    proc = subprocess.run(
        ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    match = re.search(r"mean_volume:\s*(-?[\d.]+)\s*dB", proc.stderr or "")
    return float(match.group(1)) if match else None


def check_output(
    output: Path, expect_audio: bool, loudness_target: float | None
) -> tuple[list[tuple], str]:
    """Per-file ffprobe/loudness assertions; ok=None means skipped."""
    checks: list[tuple] = []
    if shutil.which("ffprobe") is None:
        return checks, "ffprobe missing, media assertions skipped"
    try:
        media = probe_media(output)
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError):
        return checks, "ffprobe failed on output"
    checks.append(
        ("video", media["video"], "video stream present" if media["video"] else "no video stream")
    )
    checks.append(("duration", media["duration"] > 0, f"{media['duration']:.2f}s"))
    if expect_audio:
        checks.append(
            (
                "audio",
                media["audio"],
                "audio stream present" if media["audio"] else "no audio stream",
            )
        )
    if loudness_target is None:
        return checks, ""
    if shutil.which("ffmpeg") is None:
        checks.append(("loudness", None, "ffmpeg missing, loudness check skipped"))
        return checks, ""
    volume = mean_volume_db(output)
    if volume is None:
        checks.append(("loudness", False, "volumedetect produced no reading"))
    else:
        ok = abs(volume - loudness_target) <= LOUDNESS_TOL_DB
        checks.append(
            (
                "loudness",
                ok,
                f"{volume:.1f} dB vs target {loudness_target} dB (+-{LOUDNESS_TOL_DB})",
            )
        )
    return checks, ""


def run_combo(client: httpx.Client, combo: dict, project_id: str, timeout_s: float) -> dict:
    name = combo["name"]
    idea_index = combo["idea_index"]
    compose = dict(combo.get("compose") or {})
    expect_audio = bool(combo.get("expect_audio", True))
    loudness_target = compose.get("loudness_target_lufs")
    base = {
        "name": name,
        "idea_index": idea_index,
        "ok": False,
        "output": "",
        "error": "",
        "note": "",
        "rows": [],
    }

    ok, detail = apply_compose(client, project_id, compose)
    if not ok:
        base["error"] = detail
        return base

    run_id, detail = start_render(client, project_id, idea_index)
    if not run_id:
        base["error"] = detail
        return base

    terminal = wait_terminal(client, run_id, time.monotonic() + timeout_s)
    if terminal is None:
        cancel_run(client, run_id)
        base["error"] = f"timed out after {timeout_s:.0f}s"
        return base
    if terminal["event"] != "complete":
        base["error"] = f"run {terminal['event']}: {terminal['data'].get('error') or 'no detail'}"
        return base

    output = local_output_path(terminal["data"].get("output", ""))
    if not output.exists():
        base["error"] = f"output missing: {output}"
        return base
    rows, note = check_output(output, expect_audio, loudness_target)
    base["output"] = str(output)
    base["rows"] = rows
    base["note"] = note
    base["ok"] = all(row[1] is not False for row in rows)
    if not base["ok"]:
        base["error"] = "; ".join(d for _, ok, d in rows if ok is False)
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--matrix",
        default=str(DEFAULT_MATRIX),
        help="matrix yaml path (default: data/e2e_matrix.yaml)",
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("DSM_URL", DEFAULT_URL),
        help="live app base url (default: http://127.0.0.1:18080)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("DSM_AUTH_TOKEN", ""),
        help="auth token for /api/* (default: none)",
    )
    parser.add_argument("--project", default="", help="override the matrix project id")
    parser.add_argument(
        "--combos", default="", help="comma-separated subset of combo names (default: all)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=0.0,
        help="per-run timeout seconds (default: matrix timeout_s)",
    )
    args = parser.parse_args()

    matrix = load_matrix(Path(args.matrix))
    project_id = args.project or matrix["project"]
    timeout_s = args.timeout or float(matrix["timeout_s"])
    combos = select_combos(matrix, args.combos)
    params = {"token": args.token} if args.token else None

    print(
        f"matrix: {args.matrix}  project: {project_id}  "
        f"combos: {len(combos)}  timeout: {timeout_s:.0f}s"
    )
    with make_client(args.url, args.token, params) as client:
        results = [run_combo(client, combo, project_id, timeout_s) for combo in combos]

    for result in results:
        detail = result["error"] or result["note"] or result["output"]
        if not result["error"] and result["rows"]:
            detail += (
                "  ["
                + ", ".join(
                    f"{row[0]}={'ok' if row[1] else 'fail' if row[1] is False else 'skip'}"
                    for row in result["rows"]
                )
                + "]"
            )
        status = "PASS" if result["ok"] else "FAIL"
        print(f"  {result['name']:<18} idea {result['idea_index']}  {status}  {detail}")

    failed = [r for r in results if not r["ok"]]
    print(f"{len(results) - len(failed)}/{len(results)} combos passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
