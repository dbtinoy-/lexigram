# Troubleshooting

Common issues when using `lexigram-multimedia` and how to fix them.

---

## Problem: `submit()` fails — no task queue

**Error:** `UnresolvableDependencyError` (or a warning log
`multimedia_no_task_provider_bound` during boot).

**Cause:** `submit()` requires `lexigram-tasks`: a `TaskProvider` *and* a
`TaskQueueProtocol` bound in the container. Without them the provider logs a warning and
only the synchronous `generate()` path works.

**Solution:** Add the tasks module and a queue backend to your application:

```python
from lexigram.tasks.module import TasksModule

app.add_module(TasksModule.configure())
```

If you are resolving `MultimediaProvider` manually, you can also provide fakes in unit
tests by binding a `TaskProvider` and an `AsyncMock` `TaskQueueProtocol` before
`provider.boot(container)`.

---

## Problem: results come back with in-memory bytes instead of URIs

**Symptom:** `asset.has_bytes` is `True` after generation via an accessor; you expected a
blob URL.

**Cause:** No `BlobStoreProtocol` was bound at boot — the provider logs
`multimedia_no_storage_bound`. Without `lexigram-storage`, bytes assets are never
normalized to storage, in `generate()` or in submitted task handlers.

**Solution:** Configure `lexigram-storage` before the multimedia provider boots:

```python
from lexigram.storage.module import StorageModule

app.add_module(StorageModule.configure())
```

Verify in logs: the warning is gone and `normalize_asset_dict` runs (visible at DEBUG).

---

## Problem: `ProviderNotInstalledError` at startup

**Error:** `ProviderNotInstalledError: Unknown or unimplemented beat-analysis backend: 'foo'`
— or similar per subsystem.

**Cause:** Two flavors: (1) a `backend` value your installed subsystem doesn't implement;
(2) a backend whose optional extra is not installed (the sibling package raises
`ProviderNotInstalledError` eagerly at DI-resolution time so you get an actionable hint).

**Solution:** Install the extra or pick an implemented backend:

```bash
uv add "lexigram-multimedia-beat[librosa]"
```

```python
from lexigram.multimedia.beat.config import BeatAnalysisConfig

config = BeatAnalysisConfig(backend="librosa")  # "librosa" | "madmom"
```

---

## Problem: local-http backends report DEGRADED health

**Symptom:** `MultimediaProvider.health_check()` returns `DEGRADED` right after boot.
`app.startup_check()` fails on the `multimedia` component.

**Cause:** Default backends expect a local reference server you haven't started
(`http://localhost:5002` for TTS, `:5003` music, `:5004` video, `:5005` image, `:5400`
real-esrgan, `:5500` rife). The umbrella aggregates: any component below healthy makes the
whole subsystem `DEGRADED`.

**Solution:** Start the servers you rely on, or switch the backends you don't use:

```bash
lexigram-tts-chatterbox-serve   # or lexigram-tts-kokoro-serve / lexigram-tts-f5-tts-serve
lexigram-video-wan22-serve      # or lexigram-video-cogvideox-serve / lexigram-video-svd-serve
lexigram-upscale-real-esrgan-serve
lexigram-interpolate-rife-serve
```

Or use backends that need no server (e.g. the in-process `librosa` beat backend).

```yaml
multimedia:
  tts:
    backend: "local-http"
    local_http_base_url: "http://localhost:5002"
```

If a subsystem is unused, its `DEGRADED` status is informational — it does not block the
synchronous paths that don't touch that backend.

---

## Problem: generation events never arrive

**Symptom:** No `MultimediaGenerationEvent` on your event bus even though generation
succeeds.

**Cause 1:** No `EventBusProtocol` bound — the provider logs
`multimedia_no_event_bus_bound; generation events disabled`.

**Cause 2:** You resolved the raw protocol (`TTSProvider`) instead of the accessor — events
are published only from `SubsystemAccessor.generate()`.

**Solution:** bind an event bus and use the accessor path:

```python
from lexigram.events.module import EventsModule

app.add_module(EventsModule.configure())

provider = next(p for p in app.providers if p.name == "multimedia")
result = await provider.tts.generate(TTSRequest(text="hello"))  # publishes the event
```

---

## Problem: duplicate submissions reported as fresh

**Symptom:** `JobHandle.is_duplicate` is `False` on a resubmission you know is a duplicate.

**Cause:** The in-flight fast path depends on the umbrella owning its `IdempotencyManager`
(its default). If you replaced the idempotency store or bypass the provider, the flag falls
back to `JobHandle.from_idempotency_result()`'s heuristic — `status == "completed"` is the
only reliably-duplicate signal available, so a still-running duplicate is reported as fresh.

**Solution:** Keep the umbrella's wiring (`MultimediaProvider._wire_task_manager()` sets up
`InMemoryIdempotencyStoreFallback` or your bound `IdempotencyStoreProtocol` + a real
`IdempotencyManager`). For production, bind a persistent `IdempotencyStoreProtocol`:

```python
from lexigram.contracts.core.idempotency import IdempotencyStoreProtocol

# bind a persistent implementation before app.start()
```

---

## Debug Tips

- Set `LOG_LEVEL=DEBUG` to see `multimedia_services_registered`,
  `multimedia_no_storage_bound`, and subsystem discovery messages emitted by
  `MultimediaProvider`.
- Inspect `provider._sub_providers` keys: exactly seven for the core
  (`tts`, `music`, `video`, `image`, `upscale`, `interpolate`, `beat`) plus anything
  discovered via `lexigram.multimedia.subsystems`.
- Call `provider.health_check()` and read `details["components"][subsystem].to_dict()` to
  isolate which backend is degraded.
- Check task handler registration: with tasks bound, `task_provider.handlers` should
  contain `tts_generation`, `music_generation`, `video_generation`, `video_processing`,
  `upscale_generation`, `interpolate_generation`, and `timeline_render`.
- Use `MultimediaModule.stub()` in tests to avoid network and server dependencies.

---

## Still Stuck?

- Read the [Guide](./GUIDE.md) for the accessor / submit model.
- Check the sibling package docs for backend-specific errors.
- Open an issue at https://github.com/dbtinoy-/lexigram/issues