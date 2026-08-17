# Guide: lexigram-multimedia-music

Learn how to use the music generation subsystem effectively.

---

## Overview

`lexigram-multimedia-music` turns a text prompt into audio — full songs, instrumental tracks, FX, and ambient sound. It is a **backend-agnostic** layer: your code talks to the `MusicProvider` contract, and which backend answers is decided by `MusicConfig.backend`.

It is one of the `lexigram-multimedia-*` subsystems. The umbrella package `lexigram-multimedia` auto-discovers it through the `lexigram.multimedia.subsystems` entry-point group; you can also use it standalone via `AudioMusicModule`.

### When to use it

- You need generated background music, jingles, or SFX in an application.
- You want one code path that can switch between a self-hosted model and a hosted API later.
- You want generation to degrade gracefully (`Result[MediaAsset, MusicGenerationError]`, never a thrown exception for domain failures).

### When not to use it

- Speech synthesis → [`lexigram-multimedia-tts`](../lexigram-multimedia-tts/docs/QUICKSTART.md).
- Beat/tempo analysis of existing audio → `lexigram-multimedia-beat`.
- Image/video generation → the sibling `lexigram-multimedia-image` / `lexigram-multimedia-video` packages.

---

## Core Concepts

- **`MusicProvider`** — the structural protocol (from `lexigram-contracts`). Implementations expose `async generate(request: MusicRequest) -> Result[MediaAsset, MultimediaError]`. Every backend in this package satisfies it.
- **`MusicRequest`** — the frozen request value: `prompt`, `duration_seconds` (default `30.0`), `format` (default `"mp3"`), and `extra` — the escape hatch for backend-specific knobs.
- **`MediaAsset`** — the frozen result value: `mime_type`, `provider`, `bytes_data` and/or `uri`. Always check `has_bytes` / `has_uri` before consuming.
- **`MusicGenerationError`** — the package's error family (leaf of `MultimediaError`, code `LEX_ERR_MM_003`). Failures are returned inside `Err(...)`, not raised.
- **`AudioMusicProvider`** — the DI provider (name `"music"`) that reads `MusicConfig`, builds the right backend, and registers it in the container.
- **Reference servers** — small `aiohttp` servers that load a model once at startup and serve `/generate` + `/health`. They are the deployment target for the local backends.

---

## Typical Usage

### Connectionless zero-config flow

```python
import asyncio

from lexigram import Application
from lexigram.contracts.multimedia import MusicProvider, MusicRequest
from lexigram.di.module import Module, module
from lexigram.multimedia.music import AudioMusicModule


@module(imports=[AudioMusicModule.configure()])
class AppModule(Module):
    pass


async def demo() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        music: MusicProvider = await app.container.resolve(MusicProvider)
        result = await music.generate(
            MusicRequest(prompt="dark ambient drone, 60 bpm", duration_seconds=45.0)
        )
        match result:
            case _ if result.is_ok():
                asset = result.unwrap()
                print(asset.provider, asset.mime_type)
            case _:
                print(f"generation failed: {result.unwrap_err()}")


asyncio.run(demo())
```

What is happening:

- `AudioMusicModule.configure()` with no argument uses `MusicConfig()` → `backend="local-http"` → `LocalHttpMusicProvider` pointed at `http://localhost:5003`.
- One `POST {base_url}/generate` ships `{prompt, duration_seconds, format}` and the response body becomes `MediaAsset.bytes_data`.
- Because the API returns `Result`, the caller decides how to handle failure — the backend never raises for a non-200 or a timeout.

### Selecting a different backend

```python
from lexigram.multimedia.music import AudioMusicModule
from lexigram.multimedia.music.config import MusicConfig

module = AudioMusicModule.configure(
    config=MusicConfig(backend="ace-step", timeout=120.0)
)
```

Build the config from YAML instead by adding a `multimedia: music:` (or `multimedia_music:`) section to `application.yaml` — the provider's `config_key` is `"multimedia_music"`.

---

## Common Patterns

### Pattern: One codebase, many engines

The same `MusicProvider` resolution works for every backend, so deployment decides the engine, not your code:

```python
# application.yaml
multimedia_music:
  backend: "stable-audio-open"   # or local-http | ace-step | stability-audio
  stable_audio_open_base_url: "http://192.168.1.20:5301"
```

When you later need a hosted API, swap `backend` — no call-site changes.

### Pattern: Structured generation with ACE-Step

`AceStepMusicProvider` reads the ACE-Step-specific vocabulary from `extra`: `tags` (style keywords) and `lyrics`. Empty/absent lyrics means instrumental-only; non-empty lyrics produces vocals.

```python
request = MusicRequest(
    prompt="an uplifting synthwave track",
    duration_seconds=90.0,
    extra={"tags": "synthwave, driving, uplifting", "lyrics": ""},
)
```

### Pattern: Async job execution

The container also exposes `MusicGenerationTask` — a `lexigram-tasks`-compatible handler whose `run(params)` returns a JSON-serializable dict (never raw bytes), keeping the job result store happy:

```python
task: MusicGenerationTask = await app.container.resolve(MusicGenerationTask)
job_result = await task.run(
    {"prompt": "jingle for the launch video", "duration_seconds": 15.0}
)
# -> {"provider": ..., "mime_type": ..., "bytes_data": ..., "uri": ..., "metadata": ...}
```

### Pattern: Resilience without code changes

If the container has `RetryPolicyProtocol` and `CircuitBreakerProtocol` registered (e.g. from `lexigram-resilience`), the provider resolves them during `register()` and every backend automatically executes its HTTP call through `retry.execute(circuit_breaker.call, ...)`. No backend code changes; the injected retry/circuit-breaker are just wired in.

---

## Integration

- **`lexigram` core** — `Application.boot()`, the provider lifecycle (`register` → `boot`), container singleton bindings for `MusicConfig`, `MusicProvider`, and `MusicGenerationTask`.
- **`lexigram-contracts`** — `MusicProvider` protocol, `MusicRequest` / `MediaAsset` value types, and the error family (`MultimediaError` → `MusicGenerationError`, `ProviderNotInstalledError`). Defined in `lexigram.contracts.multimedia`.
- **`lexigram-resilience`** — optional; injects `RetryPolicyProtocol` + `CircuitBreakerProtocol` into every backend automatically.
- **Secrets / storage** — the provider currently needs no secrets; when a hosted backend (e.g. Stability Audio) lands, expect its key resolved via `AsyncSecretStoreProtocol` — the option is already wired in `AudioMusicProvider` (via `resolve_optional`).
- **`lexigram-multimedia` umbrella** — auto-discovery: the package registers `lexigram.multimedia.subsystems: music` and `lexigram.multimedia.modules: music` entry points, so installing it next to the umbrella lights up music capabilities with zero extra wiring.

---

## Best Practices

- ✅ Use `backend="local-http"` for development; it needs no model download and no API keys.
- ✅ Resolve `MusicProvider` from the container — never instantiate a backend class manually.
- ✅ Check `result.is_ok()` / `result.unwrap_err()` and handle both cases explicitly.
- ✅ Run reference servers in a **dedicated venv** (`pip install "lexigram-multimedia-music[ace-step-server]"`) so torch weights stay out of your app process.
- ✅ Give prompts concrete style targets (`"upbeat synthwave, 120 bpm"`) for more consistent output.
- ✅ Keep generated output out of `bytes_data` when you persist it — use `MusicGenerationTask` and let storage handle the bytes.
- ❌ Don't call `result.unwrap()` blindly — it raises on `Err`.
- ❌ Don't use `backend="stability-audio"` — it raises `ProviderNotInstalledError` at registration ("not yet implemented"); contribute an implementation instead.
- ❌ Don't set a per-request timeout smaller than `MusicConfig.timeout` — long generations are the norm, not the exception.
- ❌ Don't run heavy model servers inside the app container; keep them out-of-process and check `/health` before relying on them.

---

## Next Steps

- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Configuration](./CONFIGURATION.md) — every config key
- [Architecture](./ARCHITECTURE.md) — internal design and extension points
- [Troubleshooting](./TROUBLESHOOTING.md) — common failures and fixes