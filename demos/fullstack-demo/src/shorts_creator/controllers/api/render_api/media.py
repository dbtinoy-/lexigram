import asyncio
import os
import subprocess

from shorts_creator.controllers.api.render_api.constants import _START_LOCKS
from shorts_creator.models.asset_bundle import AssetBundle
from shorts_creator.services.asset_service import ASSETS_ROOT


def _absolutize_asset_bundle(bundle: AssetBundle) -> AssetBundle:
    """Map ASSETS_ROOT-relative paths onto absolute paths the pipeline can open.

    Public-URL sources (media_url_*) pass through untouched; the caller may
    download them via _materialize_url_bundle.
    """
    root = str(ASSETS_ROOT)
    values: dict[str, str | None] = {}
    for name in ("music_path", "font_path", "watermark_path", "bg_clip_path", "outro_clip_path"):
        path = getattr(bundle, name)
        if not path:
            values[name] = None
        elif path.lower().startswith(("http://", "https://")):
            values[name] = path
        else:
            values[name] = os.path.join(root, path)
    return AssetBundle(**values)


def _write_file(dest: str, data: bytes) -> None:
    """Write downloaded media bytes to a local temp file."""
    with open(dest, "wb") as f:
        f.write(data)


async def _materialize_url_bundle(bundle: AssetBundle, owner: str) -> AssetBundle:
    """Download URL-sourced media (bg clip / music / outro / watermark) into a
    per-owner temp dir so the pipeline can loop and seek them like local files.
    A failed download drops the role so the pipeline falls back to its defaults."""
    from urllib.parse import urlparse

    import httpx

    roles = {
        "music_path": "music",
        "bg_clip_path": "bg_clip",
        "outro_clip_path": "outro",
        "watermark_path": "watermark",
    }
    urls = {
        name: getattr(bundle, name)
        for name in roles
        if getattr(bundle, name)
        and str(getattr(bundle, name)).lower().startswith(("http://", "https://"))
    }
    if not urls:
        return bundle
    tmp_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", "data", "renders", "tmp", owner
    )
    os.makedirs(tmp_dir, exist_ok=True)
    values = {name: getattr(bundle, name) for name in roles if name not in urls}
    timeout = httpx.Timeout(60.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            for name, role in roles.items():
                url = urls.get(name)
                if not url:
                    continue
                parsed = urlparse(url)
                ext = (
                    os.path.splitext(parsed.path)[1]
                    or {
                        "music_path": ".mp3",
                        "bg_clip_path": ".mp4",
                        "outro_clip_path": ".mp4",
                        "watermark_path": ".png",
                    }[name]
                )
                dest = os.path.join(tmp_dir, f"{role}{ext}")
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    _write_file(dest, resp.content)
                    values[name] = dest
                except Exception as exc:  # noqa: BLE001 - fall back to defaults
                    print(f"[render] failed to download {role} from {url}: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"[render] URL media download failed: {exc}")
    return AssetBundle(
        music_path=values.get("music_path"),
        font_path=bundle.font_path,
        watermark_path=values.get("watermark_path"),
        bg_clip_path=values.get("bg_clip_path"),
        outro_clip_path=values.get("outro_clip_path"),
    )


def _start_lock(key: str) -> asyncio.Lock:
    return _START_LOCKS.setdefault(key, asyncio.Lock())


def probe_duration(path: str) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError, OSError):
        return 0.0


def _poster_brightness(poster_path: str) -> float:
    """Mean luma (YAVG, 0-255) of an image via ffmpeg signalstats."""
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-loglevel",
                "error",
                "-i",
                poster_path,
                "-vf",
                "signalstats,metadata=print:file=-",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        for line in result.stdout.splitlines():
            if "YAVG" in line:
                return float(line.split("=")[-1])
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
        OSError,
        ValueError,
    ):
        pass
    return -1.0


def extract_poster_frame(output_path: str) -> str:
    """Best-effort poster frame next to the master video (``<stem>.jpg``).

    Reels fade in from black, so the first frame is useless as a poster.
    Write a candidate frame at successive offsets, keeping the first
    bright-enough one. Returns the poster path, or ``""`` when extraction
    fails so renders are never blocked or marked failed by poster
    generation.
    """
    poster = os.path.splitext(output_path)[0] + ".jpg"
    if not os.path.exists(output_path):
        return ""
    duration = probe_duration(output_path) or 60.0
    candidates = [0.5, 1.5, 3.0, 6.0, 12.0, 20.0, 30.0]
    candidates += [i * duration for i in (0.5, 0.75)]
    seen: set[float] = set()
    last = ""
    try:
        for offset in candidates:
            if offset >= duration or offset in seen:
                continue
            seen.add(offset)
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-loglevel",
                    "error",
                    "-ss",
                    f"{offset}",
                    "-i",
                    output_path,
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=360:-2",
                    poster,
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )
            if os.path.exists(poster):
                last = poster
                if _poster_brightness(poster) >= 15.0:
                    return poster
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return last


def _missing_media_paths(bundle) -> list[str]:
    """Absolute-path existence pre-flight for every non-None media role."""
    missing: list[str] = []
    for role, path in (
        ("music", bundle.music_path),
        ("font", bundle.font_path),
        ("watermark", bundle.watermark_path),
        ("bg_clip", bundle.bg_clip_path),
        ("outro_clip", bundle.outro_clip_path),
    ):
        if path and not os.path.exists(path):
            missing.append(f"Missing {role} media: {path}")
    return missing
