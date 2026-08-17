# Guide

Learn how to use `lexigram-multimedia-video` effectively.

---

## Overview

`lexigram-multimedia-video` gives Lexigram applications two distinct capabilities behind two protocol boundaries:

1. **Generation** — `VideoProvider.generate(VideoRequest)` produces a new video from a prompt (optionally from frames or references). Seven backends: `local-http` (default), `runway`, `openai`, `wan22`, `cogvideox`, `svd`, `comfyui`.
2. **Processing / editing** — `VideoProcessor.process(VideoOperation)` edits existing clips with ffmpeg: trim, concat (with crossfades), overlays, composition, subtitles, audio mux, thumbnails, GIF, transcode, speed, crop, color filters, and raw filter graphs. Plus `extract_frames()` / `assemble_frames()` for frame-level pipelines.

---

## Core Concepts

- **`MediaAsset`** — the media unit: `mime_type`, `provider`, and exactly one of `bytes_data` (`has_bytes`) or `uri` (`has_uri`). Generation and processing both consume and return it.
- **`VideoRequest`** — generation input: `prompt`, `duration_seconds` (default `4.0`), `resolution` (`"1280x720"`), `image_uri`, `format` (`"mp4"`), plus reference fields (`last_frame_image`, `reference_images/videos/audios`), `generate_audio`, `return_last_frame`, `ratio`, `seed`, `extra`.
- **`VideoMode`** — `TEXT_TO_VIDEO`, `FIRST_FRAME`, `FIRST_LAST_FRAME`, `MULTIMODAL_REFERENCE`. Providers that support reference inputs derive the mode from which fields are set (`OpenAIVideoProvider._derive_mode`); `request.mode` can also be set explicitly.
- **`VideoProvider`** — the generation protocol: `async generate(request: VideoRequest) -> Result[MediaAsset, MultimediaError]`.
- **`VideoProcessor`** — the processing protocol: `process(operation, *, progress_callback=None)`, `extract_frames(asset, *, fps=None)`, `assemble_frames(frames, *, fps)`.
- **`VideoOperation`** — a discriminated union of 14 frozen dataclasses: `Trim`, `Concat`, `OverlayText`, `OverlayImage`, `ComposeVideo`, `BurnSubtitles`, `MuxAudio`, `ExtractThumbnail`, `ToGif`, `Transcode`, `ChangeSpeed`, `Crop`, `ColorFilter`, `RawFilter`. Supporting types: `TransitionSpec` (`"cut"` / `"crossfade"`), `SubtitleCue`, `ComposeLayer`, `ComposeAudioLayer`, `EncodeSpec`, `OverlayPosition`.
- **`Error` conventions** — expected failures return `Err(VideoGenerationError)` (base from contracts, `LEX_ERR_MM_004`). Package leaves: `VideoTimeoutError` (`LEX_ERR_MM_VIDEO_001`), `VideoGenerationAuthenticationError` (`LEX_ERR_MM_VIDEO_002`), `VideoProcessingError` (`LEX_ERR_MM_VIDEO_003`) — all in `lexigram.multimedia.video.exceptions`.
- **Tasks** — `VideoGenerationTask` / `VideoProcessingTask` adapt flat param dicts to `VideoRequest` / `VideoOperation` for the `lexigram-tasks` job path.

---

## Typical Usage

### Generation

```python
from lexigram.contracts.multimedia import VideoMode, VideoRequest

# Plain text-to-video (default local-http backend):
result = await video_provider.generate(VideoRequest(prompt="sunrise over a city"))

# First-frame→video (image animation):
result = await video_provider.generate(
    VideoRequest(
        prompt="a lighthouse in a storm",
        image_uri="https://cdn.example.com/lighthouse.jpg",
        duration_seconds=8.0,
    )
)
```

The backend reacts to the request shape: `image_uri` set → the provider sends it (local HTTP / Wan2.2 / CogVideoX server decide how to honor it; SVD and ComfyUI require it; OpenAI derives `FIRST_FRAME` mode).

### Processing

```python
from lexigram.contracts.multimedia import MediaAsset, OverlayText, Trim
import asyncio

clip = MediaAsset(mime_type="video/mp4", provider="local", uri="file:///tmp/clip.mp4")

async def add_watermark() -> None:
    result = await processor.process(
        OverlayText(
            asset=clip,
            text="Lexigram",
            position="bottom-right",
            font_size=28,
            color="white",
            start=0.5,
            end=3.5,
        )
    )
    return result  # Ok(MediaAsset) | Err(VideoProcessingError)
```

An asset with `has_bytes` is materialized to a temp file; a `file://` URI is used directly; any other URI is downloaded (see `materialize_asset` in `media_io.py`). Output is always read back into memory as `bytes_data`.

---

## Common Patterns

### Pattern: trim → overlay → concat a clip sequence

```python
from lexigram.contracts.multimedia import Concat, MediaAsset, OverlayText, Trim, TransitionSpec

clips = [
    MediaAsset(mime_type="video/mp4", provider="local", uri="file:///tmp/a.mp4"),
    MediaAsset(mime_type="video/mp4", provider="local", uri="file:///tmp/b.mp4"),
]

intro = await processor.process(Trim(asset=clips[0], start=1.0, end=5.0))
# intro.unwrap() is a fresh MediaAsset — feed it into the next op:
branded = await processor.process(
    OverlayText(asset=intro.unwrap(), text="Chapter 2", position="top-left")
)
out = await processor.process(
    Concat(
        assets=[branded.unwrap(), clips[1]],
        transitions=[TransitionSpec(kind="crossfade", duration=0.5)],
    )
)
```

`process()` returns a fresh `MediaAsset`, so each step's result becomes the next operation's `asset` — chain results, not the operation objects.

Crossfades become `xfade`/`acrossfade` chains in one filter graph; plain concats (or `"cut"` transitions) use the `concat` filter with a minimal-duration `xfade` epsilon for a hard cut. When a `crossfade` is present, the processor automatically probes each clip's duration (`ffprobe`) to compute the `xfade` offsets.

### Pattern: progress reporting on long operations

```python
async def report(pct: float) -> None:
    print(f"{pct:.0%}")

out = await processor.process(
    Transcode(asset=clip, format="mp4", codec="libx264"),
    progress_callback=report,
)
```

With a callback, `FFmpegVideoProcessor._run_streaming` parses `-progress pipe:1` output (`out_time` / `out_time_ms`) and emits `0.0 → 1.0` (throttled to ~1% steps, `1.0` exactly once on success).

### Pattern: frame pipeline (e.g. video upscaling with lexigram-multimedia-upscale)

```python
from lexigram.contracts.multimedia import UpscaleRequest

frames = await processor.extract_frames(clip)
# each frame: MediaAsset("image/png", provider="ffmpeg", metadata={"source_fps": ...})
worked = [await upscale_provider.upscale(UpscaleRequest(asset=f, scale_factor=2))
          for f in frames.unwrap()]
rebuilt = await processor.assemble_frames([ok.unwrap() for ok in worked], fps=30.0)
```

`assemble_frames` writes frames as sequential `frame%06d.png` files and runs ffmpeg with `-framerate <fps>`.

### Pattern: async job params (no direct protocol usage)

```python
params = {
    "operation_type": "ToGif",
    "asset": {"mime_type": "video/mp4", "provider": "local", "uri": "file:///tmp/clip.mp4"},
    "start": 0.0, "end": 3.0, "fps": 15, "width": 480,
}
out = await processing_task.run(params)  # JSON-serializable asset dict
```

`operation_type` is the dataclass class name; see `_operation_from_params` in `tasks.py` for all 14 variants.

---

## Integration

- **`lexigram` core** — provider/module lifecycle, container `singleton` bindings, `Application.boot()`.
- **`lexigram-contracts`** — `VideoProvider`, `VideoProcessor` protocols; all types under `lexigram.contracts.multimedia` (advertised convenience import path `lexigram.contracts.multimedia`).
- **`AsyncSecretStoreProtocol`** — API keys resolved **by secret name** (`resolve_credential(store, "runway_api_key")`) for Runway/OpenAI backends. Never put keys in config.
- **Resilience** — optional `RetryPolicyProtocol` / `CircuitBreakerProtocol` from the container wrap backend HTTP calls and ComfyUI submit/fetch.
- **`lexigram-multimedia-upscale`** — consumes this package's `VideoProcessor` (via contract only) through `VideoUpscaleService`.
- **`lexigram-tasks`** — task handlers for the async job path; umbrella persists result bytes to lexigram-storage.
- Discovered by the umbrella via entry points `lexigram.multimedia.subsystems` (`video`) and `lexigram.multimedia.modules` (`video`).

---

## Best Practices

- ✅ Resolve `VideoProvider` / `VideoProcessor` from the container; never construct a backend directly in app code.
- ✅ Handle `Result` explicitly — check `is_ok()` before `unwrap()`; catch task-level exceptions via `result.unwrap_err()`.
- ✅ For hosted backends, store API keys in the secrets backend and set `runway_api_key_secret_name` / `openai_api_key_secret_name` to their names.
- ✅ Prefer `file://` URIs to byte blobs for large clips feeding ffmpeg — fewer temp-file round-trips.
- ✅ Set `processing.timeout` above the longest expected operation; ffmpeg jobs are killed on timeout.
- ❌ Don't pass `image_uri` to SVD/ComfyUI without a URI the server process itself can reach.
- ❌ Don't assume every backend honors every `VideoRequest` field (e.g. `prompt` is ignored by SVD; `image_uri` handling is a server decision for CogVideoX).
- ❌ Don't run two `VideoGenerationProvider` / `VideoModule` instances in one container — backend selection is config-driven, not multi-instance.

---

## Next Steps

- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Configuration](./CONFIGURATION.md) — every config key
- [Architecture](./ARCHITECTURE.md) — internal design and extension points