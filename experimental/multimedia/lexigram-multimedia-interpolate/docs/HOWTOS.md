# How-To Guides

Task-oriented recipes for `lexigram-multimedia-interpolate`.

---

## Run the RIFE Reference Server

```bash
pip install "lexigram-multimedia-interpolate[rife-server]"
lexigram-interpolate-rife-serve
```

The `lexigram-interpolate-rife-serve` console script (entry point →
`rife_server.main`) starts an `aiohttp` app on port **5500**:

- loads `RifeModel` on startup (`cuda` if available, else `cpu`) — never
  reloaded per request
- `POST /interpolate` — body `{"frame_a_bytes": ..., "frame_b_bytes": ...}`
  (base64), returns the midpoint PNG bytes
- `GET /health` — `{"status": "ok" | "loading"}`

Verify it:

```bash
curl http://localhost:5500/health
# {"status": "ok"}
```

---

## Interpolate Two Frames

```python
import asyncio

from lexigram import Application
from lexigram.contracts.multimedia import (
    InterpolationProvider,
    InterpolationRequest,
    MediaAsset,
)
from lexigram.multimedia.interpolate import InterpolationModule


async def main() -> None:
    async with Application.boot(modules=[InterpolationModule.configure()]) as app:
        interpolate = await app.container.resolve(InterpolationProvider)
        result = await interpolate.interpolate(
            InterpolationRequest(
                frame_a=MediaAsset(
                    mime_type="image/png", provider="ffmpeg", bytes_data=read("a.png")
                ),
                frame_b=MediaAsset(
                    mime_type="image/png", provider="ffmpeg", bytes_data=read("b.png")
                ),
            )
        )
        if result.is_ok():
            with open("mid.png", "wb") as f:
                f.write(result.unwrap().bytes_data)


if __name__ == "__main__":
    asyncio.run(main())
```

Only `bytes_data` is transmitted (base64-encoded); the server keeps the
`mime_type`, `provider`, and `metadata` out of the payload entirely.

---

## Double a Video's Frame Rate

Requires a `VideoProcessor` (ffmpeg-backed) registered in the container, e.g.
via `lexigram-multimedia-video`. The provider auto-composes and registers
`VideoInterpolationService` during `register()`.

```python
from lexigram.contracts.multimedia import MediaAsset
from lexigram.multimedia.interpolate import VideoInterpolationService


service: VideoInterpolationService  # container-resolved
result = await service.interpolate_video(clip_asset, factor=2, fps=24.0)
if result.is_ok():
    doubled = result.unwrap()  # 48 fps video asset
```

Pipeline: `extract_frames(asset)` → one doubling pass (a synthesized midpoint
between every consecutive pair) → `assemble_frames(sequence, fps=48.0)`.

---

## Quadruple a Video's Frame Rate

```python
result = await service.interpolate_video(clip_asset, factor=4, fps=30.0)
if result.is_ok():
    quadrupled = result.unwrap()  # 120 fps video asset
```

`factor=4` runs **two** doubling passes: the first pass's output (with its own
midpoints) is interpolated again, then assembled at `fps * 4 = 120.0`. Expect
roughly 3 midpoint generations for a 2-frame input and an exponential jump in
frame count per pass.

---

## Submit Interpolation as a Background Job

`InterpolationTask.run(params)` is the `lexigram-tasks` submit-path handler.
Frames arrive as plain dicts and the result is a JSON-serializable dict —
never raw `MediaAsset` bytes.

```python
from lexigram.multimedia.interpolate import InterpolationTask

params = {
    "frame_a": {
        "mime_type": "image/png",
        "provider": "ffmpeg",
        "bytes_data": frame_a_bytes,   # kept as-is by the task handler
    },
    "frame_b": {"mime_type": "image/png", "provider": "ffmpeg", "bytes_data": frame_b_bytes},
    "extra": {},
}

task = InterpolationTask(backend=interpolate_provider)  # usually container-resolved
result_dict = await task.run(params)
# -> {"provider": "rife", "mime_type": ..., "bytes_data": ..., "uri": ..., "metadata": ...}
```

Under the `lexigram-multimedia` umbrella, the wrapper persists bytes into
`lexigram-storage` before the dict is built — expect `bytes_data: null` and a
filled `uri` in that deployment.

---

## Check Provider Health

```python
from lexigram.contracts.core.health import HealthStatus
from lexigram.multimedia.interpolate import InterpolationGenerationProvider

provider = await app.container.resolve(InterpolationGenerationProvider)
status = await provider.health_check(timeout=5.0)  # HealthCheckResult
if status.status is not HealthStatus.HEALTHY:
    print(f"RIFE backend {status.status.name}")
```

`InterpolationGenerationProvider.health_check()` issues `GET
{rife_base_url}/health`; any `aiohttp`/timeout failure maps to
`HealthStatus.DEGRADED`. The server itself reports `"loading"` until its model
is ready.

---

## Notes

- Both input frames must carry `bytes_data` — the provider base64-encodes
  `frame_a.bytes_data or b""`, so a URI-only `MediaAsset` silently sends empty
  frame data and the server interpolates garbage. Check `asset.has_bytes`
  first.
- `interpolate_video` returns `Err(MultimediaError("extract_frames returned an
  empty frame list"))` when the source yields zero frames — extract first,
  inspect, then interpolate.
- `RifeModel` is imported lazily by `rife_server.py` at startup; a missing
  distribution fails the server process, not the client package.