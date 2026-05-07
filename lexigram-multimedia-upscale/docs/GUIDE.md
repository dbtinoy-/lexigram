# Guide

Learn how to use `lexigram-multimedia-upscale` effectively.

---

## Overview

`lexigram-multimedia-upscale` provides **single-image super-resolution** (2x or 4x) and **frame-level video upscaling** for Lexigram applications.

- Two local reference-server backends: `real-esrgan` and `hat`.
- Both backends are thin async HTTP clients — no torch, no model weights in your application process.
- Whole-video upscaling (`VideoUpscaleService`) is composed from the video package's `VideoProcessor` protocol — no direct dependency on `lexigram-multimedia-video`.

Use it when you need to sharpen or enlarge images or video frames while staying on a plain HTTP contract.

---

## Core Concepts

- **`MediaAsset`** — the media unit throughout the multimedia subsystem. Python flag: `has_bytes` vs `has_uri`. Upscale inputs carry bytes (`bytes_data`) or a resolvable URI; outputs always carry bytes.
- **`UpscaleRequest`** — `asset: MediaAsset` + `scale_factor: Literal[2, 4] = 4` + free-form `extra`. The scale factor is a **per-request** parameter — it is not part of `UpscaleConfig`.
- **`UpscaleProvider`** — the contracts protocol: `async upscale(request: UpscaleRequest) -> Result[MediaAsset, MultimediaError]`. Your code depends on this protocol, never on a concrete backend.
- **`UpscaleError`** — domain error from `lexigram-contracts` (`LEX_ERR_MM_007`). Recoverable failures are returned as `Err(...)`, not raised.
- **Backends** — `RealEsrganUpscaleProvider` (default, port `5400`) and `HatUpscaleProvider` (port `5401`). Selected by `UpscaleConfig.backend`.
- **`UpscaleTask`** — callable task handler for the async job path (`lexigram-tasks`). Accepts a flat `params` dict, returns a plain asset dict.
- **`VideoUpscaleService`** — composes `UpscaleProvider` + `VideoProcessor`: extract frames → upscale each → reassemble at source fps.

---

## Typical Usage

```python
import asyncio

from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.multimedia.upscale import UpscaleModule
from lexigram.contracts.multimedia import MediaAsset, UpscaleProvider, UpscaleRequest


@module(imports=[UpscaleModule.configure()])
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        upscale = await app.container.resolve(UpscaleProvider)

        result = await upscale.upscale(
            UpscaleRequest(
                asset=MediaAsset(mime_type="image/png", provider="local", bytes_data=b"..."),
                scale_factor=4,
                extra={"source": "camera_raw"},
            )
        )
        if result.is_ok():
            asset = result.unwrap()
            # asset.provider == "real-esrgan", asset.mime_type echoed from the server,
            # asset.bytes_data holds the enlarged image — ready to persist or return.
        else:
            error = result.unwrap_err()  # UpscaleError
            print("upscale failed:", error)


if __name__ == "__main__":
    asyncio.run(main())
```

What is happening:

- The container resolves `UpscaleProvider` to whichever backend the config selected — callers stay backend-agnostic.
- `resolve_asset_bytes()` reads `asset.bytes_data` directly when present, or GETs `asset.uri`.
- The backend base64-encodes the image, POSTs `{"image_bytes": ..., "scale_factor": ...}` to `POST /upscale`, then wraps the response into a fresh `MediaAsset(provider="real-esrgan" | "hat")`.
- Failure is a value (`Err(UpscaleError)`), not a crash.

---

## Common Patterns

### Pattern: URI-input assets (server fetches the source)

```python
asset = MediaAsset(
    mime_type="image/png",
    provider="s3",
    uri="https://cdn.example.com/catalog/thumb.png",
)
result = await upscale.upscale(UpscaleRequest(asset=asset, scale_factor=2))
```

Use when the image already lives behind a URL. The upscale provider downloads it through `resolve_asset_bytes()` — no need to materialize it yourself.

### Pattern: Whole-video upscaling

Install and register `lexigram-multimedia-video` alongside this package, then resolve `VideoUpscaleService`:

```python
video = await app.container.resolve(VideoUpscaleService)
result = await video.upscale_video(
    MediaAsset(mime_type="video/mp4", provider="local", bytes_data=b"..."),
    scale_factor=2,
)
```

`upscale_video()` calls `VideoProcessor.extract_frames(asset)` (which records the source fps in each frame's `metadata["source_fps"]`), upscales every frame through the `UpscaleProvider`, then `assemble_frames(..., fps=source_fps)` into a new MP4. Note the method is `upscale_video`, not `upscale`: `VideoUpscaleService` is deliberately **not** an `UpscaleProvider`.

### Pattern: Resilience without touching call sites

Register a `RetryPolicyProtocol` and/or `CircuitBreakerProtocol` in the container; the `UpscaleGenerationProvider` picks them up at `register()` time and wraps backend HTTP calls automatically.

```python
# In a provider's register(): container.singleton(RetryPolicyProtocol, my_retry)
# All upscale POSTs now retry according to the policy, or open the breaker on repeated failures.
```

### Pattern: Async job submission

```python
task = await app.container.resolve(UpscaleTask)
result_dict = await task.run(
    {
        "asset": {
            "mime_type": "image/png",
            "provider": "local",
            "bytes_data": b"...",   # or "uri": "..."
            "metadata": {},
        },
        "scale_factor": 4,
        "extra": {},
    }
)
```

`UpscaleTask.run()` rebuilds an `UpscaleRequest` from the flat dict and returns a JSON-serializable asset dict (bytes-first providers must persist the payload before the umbrella serializes the job result).

---

## Integration

- **`lexigram` core** — module/provider lifecycle; container `singleton` bindings; `Application.boot()`.
- **`lexigram-contracts`** — `UpscaleProvider`, `VideoProcessor` protocols; `MediaAsset`, `UpscaleRequest` types; `UpscaleError`, `ProviderNotInstalledError` exceptions. Import path: `lexigram.contracts.multimedia`.
- **`lexigram-multimedia-video`** — provides the `VideoProcessor` (ffmpeg-backed) that activates `VideoUpscaleService`. Communication is contract-only: no direct package import.
- **`lexigram-tasks`** — `UpscaleTask` is the async job adapter; the multimedia umbrella persists result bytes to lexigram-storage.
- **`lexigram-resilience`** — optional `RetryPolicyProtocol` / `CircuitBreakerProtocol` injection.
- The multimedia umbrella discovers this subsystem via the `lexigram.multimedia.subsystems` entry point (`upscale`).

---

## Best Practices

- ✅ Resolve `UpscaleProvider` from the container; never instantiate `RealEsrganUpscaleProvider` directly in app code.
- ✅ Check `result.is_ok()` before `unwrap()` — errors are domain values.
- ✅ Keep the scale factor per-request (`UpscaleRequest.scale_factor`); the default `4` is fine for most archival upscales.
- ✅ Run reference servers in a dedicated venv — `torch`/`realesrgan`/`hat` never share your app process.
- ❌ Don't pass model weights through the app — the HTTP boundary is the whole point.
- ❌ Don't use the `hat` backend expecting a canonical PyPI install without verifying the vendored HAT inference entrypoint against your distribution.

---

## Next Steps

- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Configuration](./CONFIGURATION.md) — every config key
- [Architecture](./ARCHITECTURE.md) — internal design and extension points