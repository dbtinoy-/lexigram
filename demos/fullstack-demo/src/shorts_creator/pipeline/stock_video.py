"""Stock video sourcing for Reel backgrounds.

Replaces the old Pollinations.ai image generation (deprecated for persistent
429 rate-limiting) with real stock footage: search Pixabay, download the
best hit, then crop/scale/mute it into a portrait clip via ffmpeg. Falls
back to the existing gradient image on any failure.
"""

import asyncio
import math
import os
import random
import subprocess

import httpx

from shorts_creator.pipeline import subprocess_guard

PIXABAY_SEARCH_URL = "https://pixabay.com/api/videos/"
PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"
RETRY_BACKOFF_SECONDS = (1.0, 2.0)  # delays before retry attempts 1 and 2

DEFAULT_QUERIES = [
    "calming nature forest river",
    "ocean waves beach",
    "peaceful waterfall stream",
    "sunrise over mountains",
    "rain on leaves",
    "autumn forest",
    "snowy mountain landscape",
    "meditation nature background",
    "green forest sunlight",
    "lake reflection nature",
]

_CALM_KEYWORDS = ("stress", "anxious", "anxiety", "panic", "overwhelmed")
_CALM_QUERY_HINTS = ("calm", "waterfall", "river", "stream")
_ENERGY_KEYWORDS = ("energy", "discipline", "determination", "grind", "dawn")
_ENERGY_QUERY_HINTS = ("sunrise", "ocean", "waves")
_REST_KEYWORDS = ("rest", "peace", "meditat", "quiet", "still")
_REST_QUERY_HINTS = ("meditat",)


def query_for_line(line: str, queries: list[str] | None = None) -> str:
    """Pick a stock query for a narration line by sentiment keyword.

    Stress/anxiety lines pick a calm query, energy/discipline lines a
    sunrise or ocean query, rest/peace lines a meditation query; any other
    line picks randomly from the pool (`queries` or `DEFAULT_QUERIES`).
    Keyword-matched picks are deterministic per pool.
    """
    pool = list(queries or DEFAULT_QUERIES)
    if not pool:
        pool = list(DEFAULT_QUERIES)
    lower = line.lower()

    def _first(*hints: str) -> str | None:
        for q in pool:
            if any(h in q.lower() for h in hints):
                return q
        return None

    if any(k in lower for k in _CALM_KEYWORDS):
        picked = _first(*_CALM_QUERY_HINTS)
    elif any(k in lower for k in _ENERGY_KEYWORDS):
        picked = _first(*_ENERGY_QUERY_HINTS)
    elif any(k in lower for k in _REST_KEYWORDS):
        picked = _first(*_REST_QUERY_HINTS)
    else:
        picked = None
    return picked if picked is not None else random.choice(pool)


def _probe_duration(path: str) -> float:
    """Return media duration in seconds, or 0.0 if it can't be probed."""
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return float(proc.stdout.strip()) if proc.returncode == 0 and proc.stdout.strip() else 0.0
    except (subprocess.SubprocessError, ValueError):
        return 0.0


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


async def _with_retry(func):
    """Call `func` (no-arg async callable), retrying on transient network
    errors with a short backoff. Non-transient errors (e.g. 4xx - a bad key
    or query that won't fix itself) propagate immediately.
    """
    for attempt, delay in enumerate((0.0, *RETRY_BACKOFF_SECONDS)):
        if delay:
            await asyncio.sleep(delay)
        try:
            return await func()
        except Exception as exc:
            if not _is_transient(exc) or attempt == len(RETRY_BACKOFF_SECONDS):
                raise


async def _pixabay_search(query: str, api_key: str, category: str | None = None) -> str | None:
    """Return a direct video file URL for a random top hit, or None if no
    results. Picking randomly (rather than always the first hit) avoids every
    run reusing the identical clip for the same scene query.
    """
    params = {
        "key": api_key,
        "q": query,
        "video_type": "film",
        "safesearch": "true",
        "per_page": 20,
    }
    if category:
        params["category"] = category

    async def _do_search():
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(PIXABAY_SEARCH_URL, params=params)
            resp.raise_for_status()
            return resp.json().get("hits", [])

    hits = await _with_retry(_do_search)
    if not hits:
        return None
    videos = random.choice(hits).get("videos", {})
    for size in ("medium", "large", "small", "tiny"):
        if videos.get(size, {}).get("url"):
            return videos[size]["url"]
    return None


async def _pexels_search(query: str, api_key: str) -> str | None:
    """Return a direct video file URL for a random top hit, or None if no
    results. Portrait orientation is requested outright since Pexels (unlike
    Pixabay) supports filtering by it - a closer source crop than the
    scale+crop every clip already goes through below.
    """
    params = {"query": query, "per_page": 20, "orientation": "portrait"}
    headers = {"Authorization": api_key}

    async def _do_search():
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(PEXELS_SEARCH_URL, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json().get("videos", [])

    videos = await _with_retry(_do_search)
    if not videos:
        return None
    files = random.choice(videos).get("video_files", [])
    for quality in ("hd", "sd"):
        matches = [f["link"] for f in files if f.get("quality") == quality and f.get("link")]
        if matches:
            return random.choice(matches)
    return files[0]["link"] if files else None


async def fetch_background_video(
    query: str,
    out_path: str,
    min_seconds: float,
    width: int = 1080,
    height: int = 1920,
    category: str | None = None,
    fps: float | None = None,
    owner: str = "",
    api_keys: dict | None = None,
    provider: str = "auto",
) -> bool:
    """Download a stock clip for `query` and write a muted, portrait-cropped
    version (looped to at least `min_seconds`) to `out_path`.

    Tries every configured provider (Pixabay, Pexels) in random order per
    call - both are free-tier nature/stock sources, so trying more than one
    both adds footage variety and means one provider having no results (or
    being down/rate-limited) doesn't fall all the way back to the gradient
    image on its own. `category` is Pixabay-only (Pexels has no equivalent
    filter) and is ignored by the Pexels search.

    `api_keys` carries provider keys stored in app settings
    ({"pexels_api_key": ..., "pixabay_api_key": ...}); the PEXELS_API_KEY /
    PIXABAY_API_KEY environment variables remain the fallback when a key is
    not stored.

    `provider` pins the source: "auto" (any configured provider, shuffled)
    or "pexels"/"pixabay" to use that one when its key is configured; a
    pinned provider without a key falls back to whatever is configured.

    `fps`, if given, forces the output to that exact frame rate. The caller
    reuses this clip across many timeline segments by treating the cumulative
    project-frame count as the source's own frame index, which only works if
    the encoded fps matches the project's - stock clips arrive at whatever
    native fps they were shot at, otherwise.

    Returns True on success, False on any failure (no configured keys, no
    results from any provider, download error, ffmpeg error) so the caller
    can fall back to the gradient.
    """
    api_keys = api_keys or {}
    providers = []
    pixabay_key = api_keys.get("pixabay_api_key") or os.environ.get("PIXABAY_API_KEY")
    if pixabay_key:
        providers.append(("pixabay", pixabay_key))
    pexels_key = api_keys.get("pexels_api_key") or os.environ.get("PEXELS_API_KEY")
    if pexels_key:
        providers.append(("pexels", pexels_key))
    if not providers:
        return False
    pinned = [p for p in providers if p[0] == provider]
    if provider != "auto" and pinned:
        providers = pinned
    elif provider != "auto":
        print(
            f"   Stock provider {provider!r} pinned but not configured; using configured providers"
        )
    random.shuffle(providers)

    raw_path = out_path + ".raw.mp4"
    try:
        video_url = None
        for name, key in providers:
            try:
                if name == "pixabay":
                    video_url = await _pixabay_search(query, key, category)
                else:
                    video_url = await _pexels_search(query, key)
            except Exception as exc:  # noqa: BLE001 - try next provider on any search failure
                print(f"   {name} search failed ({type(exc).__name__}: {exc})")
                video_url = None
            if video_url:
                break
        if not video_url:
            return False

        async def _do_download():
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(video_url)
                resp.raise_for_status()
                return resp.content

        content = await _with_retry(_do_download)
        with open(raw_path, "wb") as f:  # noqa: ASYNC230 - download helper, blocking write is fine
            f.write(content)

        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            raw_path,
            "-t",
            str(min_seconds + 1),
            "-vf",
            (f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"),
            "-an",
        ]
        if fps:
            cmd += ["-r", str(fps)]
        cmd.append(out_path)
        # Run in a thread so this blocking call doesn't stall the event loop -
        # callers gather this alongside other concurrent async work (e.g.
        # narration synthesis in pipeline.py).
        await asyncio.to_thread(
            subprocess_guard.run_blocking,
            cmd,
            timeout=max(60, int(min_seconds) + 300),
            label="ffmpeg background transcode",
            owner=owner,
        )
        # -stream_loop is unreliable for some VFR / odd-timestamp stock files
        # and can silently stop at the source duration instead of looping to
        # `-t`. Verify the result and re-loop via an explicit concat list if
        # it came out short, so the background always covers the reel.
        if _probe_duration(out_path) < min_seconds:
            src_dur = _probe_duration(raw_path)
            if src_dur <= 0:
                raise RuntimeError(f"could not probe source duration: {raw_path}")
            repeats = math.ceil((min_seconds + 1) / src_dur) + 1
            list_path = out_path + ".loop.txt"
            with open(list_path, "w") as list_f:  # noqa: ASYNC230 - download helper, blocking write is fine
                list_f.writelines(f"file '{raw_path}'\n" for _ in range(repeats))
            try:
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    list_path,
                    "-t",
                    str(min_seconds + 1),
                    "-vf",
                    (
                        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                        f"crop={width}:{height}"
                    ),
                    "-an",
                ]
                if fps:
                    cmd += ["-r", str(fps)]
                cmd.append(out_path)
                await asyncio.to_thread(
                    subprocess_guard.run_blocking,
                    cmd,
                    timeout=max(60, int(min_seconds) + 300),
                    label="ffmpeg background loop",
                    owner=owner,
                )
                if _probe_duration(out_path) < min_seconds:
                    raise RuntimeError(
                        f"looped background still too short: {_probe_duration(out_path)}s < {min_seconds}s"
                    )
            finally:
                if os.path.exists(list_path):
                    os.remove(list_path)
        return True
    except Exception as exc:  # noqa: BLE001 - fetch failure degrades to fallback background
        print(f"   Stock video fetch failed ({type(exc).__name__}: {exc})")
        return False
    finally:
        if os.path.exists(raw_path):
            os.remove(raw_path)
