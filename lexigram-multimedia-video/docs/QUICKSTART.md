# Quickstart

Get video generation and editing running in minutes.

---

## Install

```bash
uv add lexigram-multimedia-video
# Optional: local reference-server dependencies (torch)
uv add "lexigram-multimedia-video[wan22-server]"          # Wan2.2 server
uv add "lexigram-multimedia-video[cogvideox-server]"      # CogVideoX server
uv add "lexigram-multimedia-video[svd-server]"            # SVD server
# Optional extras for hosted APIs
uv add "lexigram-multimedia-video[runway]"                # Runway API
uv add "lexigram-multimedia-video[openai]"                # OpenAI video gateway
```

`lexigram-multimedia-video` depends on `lexigram`, `lexigram-contracts`, and `aiohttp`. The `VideoProcessor` (editing) additionally requires the **`ffmpeg` binary on `PATH`** — without it the processor simply is not registered.

The default backend is `local-http` against `http://localhost:5004` — no API keys needed.

---

## Minimal Video Generation

```python
import asyncio

from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.multimedia.video import VideoModule
from lexigram.contracts.multimedia import VideoProvider, VideoRequest


@module(imports=[VideoModule.configure()])
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        video = await app.container.resolve(VideoProvider)

        result = await video.generate(
            VideoRequest(prompt="a drone flying over misty mountains")
        )
        if result.is_ok():
            asset = result.unwrap()  # MediaAsset — MP4 bytes or URI
            print("generated:", asset.provider, asset.mime_type)


if __name__ == "__main__":
    asyncio.run(main())
```

With an `application.yaml`:

```yaml
multimedia:
  video:
    backend: "local-http"
    local_http_base_url: "http://localhost:5004"
```

---

## Minimal Video Processing (needs ffmpeg)

```python
from lexigram.contracts.multimedia import MediaAsset, Trim
from lexigram.contracts.multimedia.protocols import VideoProcessor

processor = await app.container.resolve(VideoProcessor)

result = await processor.process(
    Trim(
        asset=MediaAsset(mime_type="video/mp4", provider="local", bytes_data=mp4_bytes),
        start=1.0,
        end=4.0,
    )
)
if result.is_ok():
    trimmed = result.unwrap()  # MediaAsset(provider="ffmpeg", mime_type="video/mp4")
```

`VideoModule` exports both `VideoProvider` (generation) and `VideoProcessor` (editing) when `ffmpeg` is available.

---

## What Just Happened

1. `VideoModule.configure()` creates a `DynamicModule` with a `VideoGenerationProvider`.
2. `Application.boot()` runs registration:
   - `VideoConfig` is bound in the container.
   - The configured generation backend is constructed (`LocalHttpVideoProvider` by default) and bound as `VideoProvider`; a `VideoGenerationTask` handler wraps it.
   - If `ffmpeg` is found on `PATH`, an `FFmpegVideoProcessor` is built from `VideoProcessingConfig` and bound as `VideoProcessor`, plus a `VideoProcessingTask`.
   - Optional `AsyncSecretStoreProtocol` (API keys), `RetryPolicyProtocol`, and `CircuitBreakerProtocol` are picked up from the container.
3. `generate(VideoRequest(prompt=...))` POSTs the request to `/generate` and returns `Ok(MediaAsset)` — or `Err(VideoGenerationError)`. `process(VideoOperation)` runs an ffmpeg subprocess and returns a `MediaAsset` in bytes.

---

## Next Steps

- [Guide](./GUIDE.md) — mental model: generation, processing, operations
- [How-Tos](./HOWTOS.md) — task-oriented recipes (trim, concat, compose, subtitles, GIF, …)
- [Configuration](./CONFIGURATION.md) — every config key and env-var override
- [Architecture](./ARCHITECTURE.md) — internal design and extension points