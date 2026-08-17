# Guide

Learn how to use `lexigram-multimedia-beat` for tempo and beat detection.

---

## Overview

`lexigram-multimedia-beat` analyzes an audio `MediaAsset` and returns a
`BeatAnalysisResult` with two fields: `tempo_bpm` (float) and `beat_timestamps`
(list of floats, seconds). It is a **sync-only** subsystem — no blob persistence, no queue,
no `submit()` path — because the output is a small pure value that callers use immediately,
typically to drive beat-synced video cut timing.

Two backends are available:

| Backend | Deployment | Accuracy | Dependencies |
|---------|-----------|----------|--------------|
| `librosa` (default) | In-process, no server | Good; classic spectral-flux tracker | `librosa` extra, CPU-only |
| `madmom` | Separate reference server (HTTP) | Better on syncopated / tempo-changing material | `madmom-server` extra |

The package also ships the reference server itself: `lexigram-beat-madmom-serve` runs a
small aiohttp service that hosts the madmom model.

---

## Core Concepts

- **`BeatAnalysisModule`** — the DI entry point. `configure()` for production,
  `stub()` for tests (forces the `librosa` backend).
- **`BeatAnalysisConfig`** — `backend`, `librosa_sample_rate`, `madmom_base_url`,
  `timeout`. Section name `multimedia_beat`.
- **`BeatAnalysisProvider`** — the protocol from `lexigram.contracts.multimedia`:
  `analyze(request) -> Result[BeatAnalysisResult, MultimediaError]`.
- **`BeatAnalysisRequest`** — wraps one `MediaAsset` (bytes or URI) plus `extra`.
- **`BeatAnalysisResult`** — `tempo_bpm: float`, `beat_timestamps: list[float]`.
- **`BeatAnalysisDecodeError`** — raised as `Err` inside a `Result` when librosa cannot
  decode the audio file.
- **The madmom HTTP contract** — `POST /analyze` with JSON
  `{"audio_bytes": "<base64>"}` returns `{"tempo_bpm": ..., "beat_timestamps": [...]}`;
  `GET /health` returns `{"status": "ok" | "loading"}`.

---

## Typical Usage

```python
from lexigram import Application
from lexigram.contracts.multimedia.protocols import BeatAnalysisProvider
from lexigram.contracts.multimedia.types import BeatAnalysisRequest, MediaAsset
from lexigram.multimedia.beat import BeatAnalysisModule


app = Application(name="beat-sync")
app.add_module(BeatAnalysisModule.configure())
await app.start()

beat = await app.container.resolve(BeatAnalysisProvider)

# URI-backed asset (already in blob storage) is also supported
asset = MediaAsset(mime_type="audio/wav", provider="storage", uri="s3://bucket/track.wav")
result = await beat.analyze(BeatAnalysisRequest(asset=asset))
if result.is_err():
    print("analysis failed:", result.unwrap_err())
else:
    analysis = result.unwrap()
    downbeats = [t for i, t in enumerate(analysis.beat_timestamps) if i % 4 == 0]
    print(analysis.tempo_bpm, downbeats[:4])
```

Errors are expressible **values**, not exceptions: unwrap with `is_ok()` / `is_err()`, and
handle expected failures (bad audio, madmom down) in your own control flow.

---

## Common Patterns

### Pattern: Beat-synced cut timing

```python
result = await beat.analyze(BeatAnalysisRequest(asset=mix))
if result.is_ok():
    analysis = result.unwrap()
    wav_timestamps = analysis.beat_timestamps
    cuts = [t for t in wav_timestamps if 2.0 <= t <= 20.0]
    video = provider.video
    for i, (start, end) in enumerate(zip(cuts, cuts[1:])):
        handle = await video.submit_process(
            Trim(asset=master, start=start, end=end),
            idempotency_key=f"cut-{i}-{start:.2f}",
        )
```

### Pattern: Falling back between backends

```python
from lexigram.multimedia.beat.config import BeatAnalysisConfig
from lexigram.multimedia.beat import BeatAnalysisModule

# Try the precise DL backend first; fall back to in-process librosa on failure
app.add_module(
    BeatAnalysisModule.configure(config=BeatAnalysisConfig(backend="madmom"))
)
```

If the madmom server is unreachable, `analyze()` returns
`Err(MultimediaError("Madmom request failed: ..."))` — switch `backend` back to
`"librosa"` and retry in your application logic.

### Pattern: Running through the umbrella

When installed alongside `lexigram-multimedia`, the beat subsystem is wired by the
umbrella — `config.beat` nests under `multimedia:` and the accessor is
`MultimediaProvider.beat`:

```python
from lexigram.multimedia import MultimediaModule


app.add_module(MultimediaModule.configure())
await app.start()

provider = next(p for p in app.providers if p.name == "multimedia")
result = await provider.beat.analyze(BeatAnalysisRequest(asset=asset))
```

---

## Integration

- **`lexigram-multimedia` (umbrella)** — the umbrella's `MultimediaProvider.register()`
  constructs `BeatAnalysisGenerationProvider(config=self._config.beat)` and its `.beat`
  accessor delegates to the bound backend. The beat subsystem's `lexigram.multimedia.subsystems`
  entry point (`beat → BeatAnalysisGenerationProvider`) is what registers it.
- **`lexigram-resilience`** — optional. When `RetryPolicyProtocol` and/or
  `CircuitBreakerProtocol` are bound, `MadmomBeatAnalysisProvider` wraps its HTTP call in
  them (retry → circuit-breaker → raw post).
- **`lexigram-contracts`** — the protocol and value types live in
  `lexigram.contracts.multimedia`; `BeatAnalysisError` (`LEX_ERR_MM_008`) is the base
  exception, extended by `BeatAnalysisDecodeError` in this package
  (`LEX_ERR_MM_BEAT_003`).
- **Contracts → your services** — a downstream composer service injects
  `BeatAnalysisProvider` as a typed constructor parameter and uses the timestamps to
  schedule `lexigram-multimedia-video` operations.

---

## Best Practices

- ✅ Use `librosa` for UIs, batch jobs, and CI — zero servers, fast cold start.
- ✅ Use `madmom` for syncopated, tempo-changing, or percussion-heavy material.
- ✅ Bootstrap the madmom server in a dedicated venv and keep it warm — it loads the model
  once at startup.
- ✅ Handle decode failures through `Result`: check `.is_err()` and surface the message.
- ❌ Don't expect a `submit()`/queue path — this subsystem is sync-only by design.
- ❌ Don't run a madmom server per request; it loads a DL model at startup and never
  per-request.
- ❌ Don't pass `np.ndarray`-shaped data anywhere — the request contract is a `MediaAsset`
  (bytes or URI) and the response is plain floats.

---

## Next Steps

- [How-Tos](./HOWTOS.md) — start the madmom server, choose backends, resilience recipes
- [Configuration](./CONFIGURATION.md) — every config key and env var
- [Architecture](./ARCHITECTURE.md) — provider internals and server protocol