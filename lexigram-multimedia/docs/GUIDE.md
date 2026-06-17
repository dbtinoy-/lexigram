# Guide

Learn how to use `lexigram-multimedia` to generate and compose media across every subsystem.

---

## Overview

`lexigram-multimedia` is the **orchestration layer** for the Lexigram multimedia subsystem.
One module wires **seven independent generation packages** into a single DI graph:

| Subsystem | Package | Protocol | Default backend |
|-----------|---------|----------|-----------------|
| Text-to-speech | `lexigram-multimedia-tts` | `TTSProvider` | `local-http` |
| Music | `lexigram-multimedia-music` | `MusicProvider` | `local-http` |
| Video | `lexigram-multimedia-video` | `VideoProvider` + `VideoProcessor` | `local-http` |
| Image | `lexigram-multimedia-image` | `ImageProvider` | `local-http` |
| Upscale | `lexigram-multimedia-upscale` | `UpscaleProvider` | `real-esrgan` |
| Interpolate | `lexigram-multimedia-interpolate` | `InterpolationProvider` | `rife` |
| Beat analysis | `lexigram-multimedia-beat` | `BeatAnalysisProvider` | `librosa` |

Use this package when your application generates more than one media type, needs
**async job submission** (generation off the request path), **blob-backed asset storage**,
or **timeline composition**. For a single subsystem, you can use that subsystem's module
directly instead — the umbrella is intentionally additive, not mandatory.

---

## Core Concepts

- **`MultimediaModule`** — the DI entry point. `configure(config)` for production,
  `stub()` for tests and local development it discovers every installed subsystem.
- **`MultimediaConfig`** — a single nested config with one sub-config per subsystem plus
  `storage_path_prefix` and `cache_results`.
- **Protocols** — `TTSProvider`, `MusicProvider`, `VideoProvider`, `ImageProvider`,
  `UpscaleProvider`, `InterpolationProvider`, `BeatAnalysisProvider`, `VideoProcessor`.
  Resolve these from the container to call a backend directly.
- **Accessors** — higher-level facades on top of the raw backends. Add storage
  normalization, an idempotency signal, result caching, and generation events.
  Exposed as properties on `MultimediaProvider`: `.tts`, `.music`, `.video`, `.image`,
  `.upscale`, `.interpolate`, `.beat`, `.compose`.
- **`MediaAsset`** — the universal result type. Carries either `bytes_data` or `uri`,
  `mime_type`, `provider`, and `metadata`. Check `has_bytes` / `has_uri` — providers
  differ (ElevenLabs/OpenAI return bytes; hosted backends return URIs).
- **`JobHandle`** — the queued-submission handle. `submit()` returns it instead of running
  inline; it has `job_id`, `status`, and `is_duplicate`.
- **`Timeline`** — a mutable builder for video composition (clips, narration, music,
  captions, overlays, fades).

---

## Typical Usage

The most common production shape is to resolve a protocol and call `generate()`, letting
the accessor do the heavy lifting.

```python
from lexigram import Application
from lexigram.contracts.multimedia import MusicProvider, MusicRequest
from lexigram.multimedia import MultimediaModule


app = Application(name="jukebox")
app.add_module(MultimediaModule.configure())
await app.start()

music = await app.container.resolve(MusicProvider)
result = await music.generate(
    MusicRequest(prompt="lofi hip-hop, warm keys, vinyl crackle", duration_seconds=45.0)
)
if result.is_ok():
    track = result.unwrap()   # MediaAsset — now normalized into blob storage
else:
    print("Failed:", result.unwrap_err())
```

**What's happening:** resolving `MusicProvider` gives the concrete music backend, wired by
the umbrella's `MultimediaProvider`. Because the umbrella also bound `BlobStoreProtocol` in
`boot()`, the request flows through the live backend, and the returned `MediaAsset` is
already URI-backed — no manual upload step.

**Why accessors matter:** calling the protocol gives you the asset, but the accessors
supply the extras — result caching (when `cache_results` is true), an idempotency flag on
submission, and a `MultimediaGenerationEvent` on the event bus. Both paths are valid;
accessors are the full-featured route.

---

## Common Patterns

### Pattern: Queued generation (background job)

```python
from lexigram.contracts.multimedia import TTSRequest


# The umbrella provider is reachable via app.providers (by name)
provider = next(p for p in app.providers if p.name == "multimedia")

tts = provider.tts
handle = await tts.submit(TTSRequest(text="Long narration for a video"), idempotency_key="narration-v1")
print(handle.job_id, handle.status)
```

Use `submit()` when generation may exceed your HTTP request budget. The task is dispatched
to `lexigram-tasks`, deduplicated by `idempotency_key`, and the result asset is normalized
to storage by the task handler when it completes. Resubmitting with the same key returns a
duplicate `JobHandle`.

> **Note:** `MultimediaProvider` is a provider, not a container service — it is not
> registered for `container.resolve()`. Access it through `app.providers` (or keep a
> reference to the instance you pass to `MultimediaModule.configure()`).

### Pattern: Video processing pipeline

```python
from lexigram.contracts.multimedia import Trim


provider = next(p for p in app.providers if p.name == "multimedia")
video = provider.video
trimmed = await video.process(Trim(asset=source, start=5.0, end=20.0))
my_clip = await video.submit_process(
    Trim(asset=source, start=5.0, end=20.0), idempotency_key="trim-intro"
)
```

`VideoAccessor` exposes **both** generation (`.generate` / `.submit`) and **processing**
(`.process` / `.submit_process`). Processing runs ffmpeg-backed operations
(`Trim`, `Concat`, `ComposeVideo`, `MuxAudio`, `BurnSubtitles`, `Transcode`, `Crop`,
`RawFilter`, …).

### Pattern: Timeline composition

```python
from lexigram.contracts.multimedia import MediaAsset, SubtitleCue, TransitionSpec


timeline = Timeline()
timeline.add_clip(clip_a, transition_in=TransitionSpec(kind="cut"))
timeline.add_clip(clip_b, transition_in=TransitionSpec(kind="crossfade", duration=0.4))
timeline.set_music(bgm, duck_under_narration=True)
timeline.add_captions([SubtitleCue(start=0.0, end=2.0, text="Intro")])
timeline.set_fade_in(0.5)
timeline.set_fade_out(0.5)

result = await provider.compose.render(timeline)          # sync
handle = await provider.compose.submit_render(timeline)   # queued
```

### Pattern: Whole-video post-processing

```python
upscaled = await provider.video.upscale_video(source, scale_factor=4)   # needs VideoProcessor
smoothed = await provider.video.interpolate_video(source, factor=2, fps=60.0)
```

These return `Result[MediaAsset, MultimediaError]` and produce
`Err(ProviderNotInstalledError)` when the upscale/interpolate subsystem was configured
without a video processor.

---

## Integration

- **`lexigram-storage`** — optional. If a `BlobStoreProtocol` is bound, submission
  uploads bytes-carrying assets before they cross the task queue, and finished results
  are normalized to URIs.
- **`lexigram-tasks`** — optional. Without it only the synchronous `generate()` path
  works; `submit()` requires a `TaskQueueProtocol` + a `TaskProvider`. When present, the
  umbrella registers task handlers for `tts_generation`, `music_generation`,
  `video_generation`, `video_processing`, `upscale_generation`, `interpolate_generation`,
  and `timeline_render`.
- **`lexigram-cache`** — optional. When a `CacheBackendProtocol` is bound **and**
  `cache_results: true`, accessor `generate()` results are cached by canonical-JSON +
  sha256 key (`multimedia:{task_name}:{digest}`).
- **`lexigram-events`** — optional. When an `EventBusProtocol` is bound, each successful
  accessor `generate()` publishes a `MultimediaGenerationEvent` (`media_type`, `provider`,
  `size_bytes`, `duration_seconds`) mirroring the `lexigram-ai-llm` observability pattern.
- **`lexigram-resilience`** — optional. `RetryPolicyProtocol` and `CircuitBreakerProtocol`
  are wired into the `madmom` beat backend and other resilient clients.
- **Contracts** — all types and protocols come from `lexigram.contracts.multimedia`;
  the round-trip is contract → provider → accessor → your service.

---

## Best Practices

- ✅ Configure the umbrella once at composition root: `app.add_module(MultimediaModule.configure())`.
- ✅ Use accessors (`provider.video`, `provider.tts`) when you need storage, caching,
  events, or idempotent submission.
- ✅ Pass an `idempotency_key` on `submit()` calls you may retry.
- ✅ Check `asset.has_uri` / `asset.has_bytes` before assuming how to consume an asset.
- ✅ Add a subsystem's extra only when you really need a remote/GPU backend —
  `local-http` and `librosa` need no server.
- ❌ Don't import sibling packages directly; resolve protocols from the container.
- ❌ Don't omit the `lexigram-storage` provider and then expect `submit()` results to be
  URIs — bytes assets stay in-memory and storage normalization is skipped.
- ❌ Don't `unwrap()` a `Result` without an `is_ok()` / `is_err()` guard.

---

## Next Steps

- [How-Tos](./HOWTOS.md) — concrete recipes per subsystem
- [Configuration](./CONFIGURATION.md) — the nested `multimedia:` config tree
- [Architecture](./ARCHITECTURE.md) — provider wiring, lifecycle, extension points