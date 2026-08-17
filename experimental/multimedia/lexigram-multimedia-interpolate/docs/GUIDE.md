# Guide

Understand and use `lexigram-multimedia-interpolate` effectively.

---

## Overview

`lexigram-multimedia-interpolate` synthesizes frames between two input frames
using a **RIFE** (Real-Time Intermediate Flow Estimation) reference server,
and — when a `VideoProcessor` is available — doubles or quadruples a whole
video's frame rate. It is the interpolation piece of the
`lexigram-multimedia` umbrella: frame-pair work happens here, video-level work
composes this package's `InterpolationProvider` with the video package's
`VideoProcessor` protocol.

Two distinct APIs are offered:

| API | Entry point | Input → Output |
|-----|-------------|----------------|
| Frame-pair interpolation | `InterpolationProvider.interpolate(InterpolationRequest)` | 2 frames → 1 midpoint frame |
| Full-video interpolation | `VideoInterpolationService.interpolate_video(asset, factor, fps)` | 1 video → factor× fps video |

---

## Core Concepts

- **`InterpolationProvider`** — the structural contract
  (`lexigram.contracts.multimedia.protocols`):
  `async interpolate(request: InterpolationRequest) -> Result[MediaAsset, MultimediaError>`.
  `RifeInterpolationProvider` is the only implementation and matches it
  structurally.
- **`InterpolationRequest`** — frozen dataclass: `frame_a: MediaAsset`,
  `frame_b: MediaAsset`, and an `extra: dict` (currently unused by the RIFE
  backend, reserved for future backends).
- **`MediaAsset`** — frozen result value carrying `mime_type`, `provider`,
  `bytes_data`/`uri`, `metadata`. Input and output frames are all `MediaAsset`s.
- **`RifeInterpolationProvider`** — HTTP client to a local reference server.
  Base64-encodes `frame_a.bytes_data` and `frame_b.bytes_data` and POSTs to
  `{base_url}/interpolate`; the response body (PNG) becomes the result asset.
- **`VideoInterpolationService`** — higher-level composition, **not** an
  `InterpolationProvider`. It extracts frames from a source video via
  `VideoProcessor.extract_frames`, inserts `factor/2` midpoint passes for each
  consecutive pair (`_double`), and reassembles at `fps * factor` with
  `VideoProcessor.assemble_frames`. Registered in the container only when a
  `VideoProcessor` is present.
- **`InterpolationTask`** — the `lexigram-tasks` bridge. `run(params)` rebuilds
  `frame_a`/`frame_b` from plain dicts (via `_asset_from_params`) and returns a
  JSON-serializable result dict.
- **`rife_server.py`** — the packaged reference server: an `aiohttp` web app
  that loads a `RifeModel` once at startup (CUDA if available, else CPU),
  answers `POST /interpolate` and `GET /health`, and runs on port 5500 via the
  `lexigram-interpolate-rife-serve` console script.

---

## Typical Usage

### Frame-Pair Interpolation

```python
from lexigram import Application
from lexigram.contracts.multimedia import (
    InterpolationProvider,
    InterpolationRequest,
    MediaAsset,
)
from lexigram.multimedia.interpolate import InterpolationModule


async def create_midframe() -> None:
    async with Application.boot(modules=[InterpolationModule.configure()]) as app:
        interpolate = await app.container.resolve(InterpolationProvider)

        result = await interpolate.interpolate(
            InterpolationRequest(
                frame_a=MediaAsset(mime_type="image/png", provider="ffmpeg", bytes_data=fa),
                frame_b=MediaAsset(mime_type="image/png", provider="ffmpeg", bytes_data=fb),
            )
        )
        if result.is_ok():
            midpoint = result.unwrap()  # MediaAsset(provider="rife")
```

What is happening:

- Both source frames travel as `MediaAsset` — the same value type the rest of
  the multimedia family returns, so frames extracted from a video can be fed
  straight in.
- The backend is resolved through the container; the response is a
  `MediaAsset` from provider `"rife"` with the server's `Content-Type`
  (`image/png` by default).

### Full-Video Interpolation (VideoInterpolationService)

```python
async def double_fps(asset: MediaAsset) -> None:
    async with Application.boot(modules=[InterpolationModule.configure()]) as app:
        service = await app.container.resolve(VideoInterpolationService)
        result = await service.interpolate_video(asset, factor=2, fps=24.0)
        # assemble_frames called with fps=48.0
```

This only works when a `VideoProcessor` (ffmpeg-backed, from
`lexigram-multimedia-video`) is registered in the container — otherwise
`VideoInterpolationService` is not registered and resolution fails.

---

## Common Patterns

### Pattern: Whole-Video Pipeline via Factor 4

`interpolate_video(asset, factor=4, fps=x)` runs **two** doubling passes:
the already-doubled sequence is interpolated again, so the frame count
quadruples and assembly runs at `fps * 4`.

```python
result = await service.interpolate_video(asset, factor=4, fps=30.0)  # → 120 fps
```

### Pattern: Chain Interpolation with Other Media Operations

```python
mid = midframes_result.unwrap()                      # interleaved sequence
assembled = await video_processor.assemble_frames(sequence, fps=48.0)
```

The service is deliberately *not* an `InterpolationProvider`: its method is
`interpolate_video`, not `interpolate`, and its signature is whole-video +
factor, mirroring how video upscaling keeps a separate service type. Compose at
the service level, not the protocol level.

---

## Integration

- **`lexigram-multimedia` umbrella** — discovered via the
  `lexigram.multimedia.subsystems` / `lexigram.multimedia.modules` entry
  points; config nests under `multimedia: interpolate:`, and the umbrella
  wraps the task handler to persist result bytes into `lexigram-storage`.
- **`lexigram-multimedia-video`** — via the `VideoProcessor` protocol only,
  never a direct import: `extract_frames`, `assemble_frames`, `process` on
  `VideoOperation`s. This is the reason `VideoInterpolationService` exists in
  this package at all.
- **`lexigram-tasks`** — `InterpolationTask.run()` is the submit path; errors
  from the backend are raised (recorded on the job).
- **Resilience** — `RetryPolicyProtocol` / `CircuitBreakerProtocol` from the
  container wrap the HTTP call automatically.
- **Health checks** — `InterpolationGenerationProvider.health_check()` probes
  `GET {rife_base_url}/health`.

---

## Best Practices

- ✅ Run the RIFE server in a dedicated venv with the `[rife-server]` extra —
  PyTorch never touches your application environment.
- ✅ Verify `RifeModel` import/install against your RIFE distribution — there is
  no single official PyPI package; `rife_server.py` imports it lazily at
  startup.
- ✅ Feed frames extracted by `VideoProcessor.extract_frames` straight into
  `InterpolationRequest` — both sides speak `MediaAsset`.
- ✅ Use `InterpolationModule.stub()` in tests; it pins the real `rife`
  backend without needing a live server.
- ❌ Don't construct `VideoInterpolationService` manually in production —
  resolve it from the container so `register()` wires it with the same backend
  and `VideoProcessor` instances.
- ❌ Don't expect `interpolate()` to accept videos — it takes two frames; use
  `VideoInterpolationService.interpolate_video()` for clips.
- ❌ Don't rely on `MediaAsset` carrying both bytes and a URI — check
  `has_bytes` / `has_uri` after results cross process boundaries.

---

## Next Steps

- [How-Tos](./HOWTOS.md) — run the server, interpolate videos, background jobs
- [Configuration](./CONFIGURATION.md) — every config key
- [Architecture](./ARCHITECTURE.md) — internal design and extension points