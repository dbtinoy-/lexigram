# Troubleshooting: lexigram-multimedia-music

Common issues with music generation and how to fix them. Error text comes from the package source; identifiers cross-reference `src/lexigram/multimedia/music/`.

---

## Problem: `ProviderNotInstalledError: backend='stability-audio' is not yet implemented`

**Cause:** `MusicConfig.backend` is set to `"stability-audio"`, but `StabilityAudioMusicProvider` is a deliberate stub (see `providers/stability_audio.py`). The provider raises this eagerly during `register()` — it does not wait for a request.

**Solution:** Use a different backend:

```python
from lexigram.multimedia.music import AudioMusicModule
from lexigram.multimedia.music.config import MusicConfig

module = AudioMusicModule.configure(config=MusicConfig(backend="local-http"))
```

Or, if you want the hosted Stability API, implement it: add the branch in `AudioMusicProvider.register()` and replace the stub class.

---

## Problem: `MusicGenerationError: ... request failed: <ClientError>`

**Cause:** The backend server is unreachable — not running, wrong host/port, or no route. Every HTTP backend wraps `aiohttp.ClientError` / `TimeoutError` into `Err(MusicGenerationError(...))`, so this surfaces as an `Err` on `generate()`, not a crash.

**Solution:** Confirm the server is up and reachable, and that the base URL in config matches:

```bash
curl http://localhost:5003/health     # local-http
curl http://localhost:5300/health     # ace-step
curl http://localhost:5301/health     # stable-audio-open
```

```python
config = MusicConfig(ace_step_base_url="http://localhost:5300")
# ensure AudioMusicModule.configure(config=config) uses the same URL
```

Check `result` explicitly:

```python
result = await music.generate(MusicRequest(prompt="x"))
if result.is_err():
    print("failed:", result.unwrap_err())
```

---

## Problem: `MusicGenerationError: <provider> server returned 404: b'...'`

**Cause:** The server is up but the `/generate` route is missing or differs from the expected wire shape. Backends POST to `{base_url}/generate` with `{prompt, duration_seconds, format}` (plus `tags`/`lyrics` for ACE-Step). A square peg at the wrong path returns 404 and the body is included in the error.

**Solution:** Verify the exact route and payload the server expects:

```python
# what AceStepMusicProvider sends
payload = {"prompt": request.prompt, "duration_seconds": request.duration_seconds,
           "format": request.format, "tags": request.extra.get("tags", ""),
           "lyrics": request.extra.get("lyrics", "")}
```

Prefer the shipped reference servers (`lexigram-music-ace-step-serve`, `lexigram-music-stable-audio-open-serve`); they implement the matching contract on `:5300` / `:5301`.

---

## Problem: Generation "succeeds" but output is empty / wrong length

**Cause:** The response `Content-Type` and body length come straight from the server. `LocalHttpMusicProvider` trusts `Content-Type` (defaulting to `audio/mpeg`); the model servers return native WAV regardless of `request.format`. If the model silently clamps length (Stable Audio Open's ~47s ceiling), you get a shorter track, not an error.

**Solution:**

```python
asset = result.unwrap()
print(asset.mime_type, len(asset.bytes_data or b""))
print(asset.provider)
```

Keep `duration_seconds` within the model's native window for Stable Audio Open; use ACE-Step for long full songs. Treat `request.format` as advisory for the local backends.

---

## Problem: `ProviderNotInstalledError` when starting an ACE-Step server

**Cause:** The console script imports `ace_step.AceStepPipeline` and `torch` at startup. If the `ace-step-server` extra isn't installed in that venv, or the installed ACE-Step version's API differs from this reference server's signature, startup fails.

**Solution:** Install into a dedicated venv and verify the model's constructor/inference signature against the actually-installed version:

```bash
pip install "lexigram-multimedia-music[ace-step-server]"
lexigram-music-ace-step-serve
```

```python
# server startup loads the pipeline once:
#   pipeline = AceStepPipeline.from_pretrained(device="cuda" if torch.cuda.is_available() else "cpu")
```

ACE-Step is young and actively developed (a known risk in the design spec) — check the installed package's API before relying on it in production.

---

## Problem: Health reports `DEGRADED` or `UNHEALTHY`

**Cause:** `AudioMusicProvider.health_check()` returns:

- `UNHEALTHY` when `self._backend is None` (registration never ran),
- `DEGRADED` when the `/health` probe is non-200, times out, or raises `aiohttp.ClientError`/`OSError`,
- `HEALTHY` only on a 200 from `{base_url}/health`.

**Solution:**

```python
await provider.health_check(timeout=5.0)   # -> HealthCheckResult
```

Make sure the backend is actually started. Note: **non-HTTP backends** (not currently selectable here) short-circuit to `HEALTHY` since they have no liveness endpoint.

---

## Problem: Manual backend instantiation doesn't behave like the wired one

**Cause:** When you construct a backend class by hand, optional resilience (`retry`, `circuit_breaker`) is absent unless you supply it — so you lose the retry/circuit-breaker wrapping the DI path provides automatically.

**Solution:** Resolve from the container instead so `AudioMusicProvider.register()` builds the fully-wired instance:

```python
music: MusicProvider = await app.container.resolve(MusicProvider)
```

```python
# Manual construction — you must pass resilience yourself:
provider = AceStepMusicProvider(
    base_url="http://localhost:5300",
    timeout=120.0,
    retry=retry_policy,          # rarely what you want by hand
    circuit_breaker=breaker,
)
```

---

## Debug Tips

- Enable debug logging to see registration events: set log level to `DEBUG` — the provider logs `music_registered` with the chosen backend.
- Confirm which backend is active by reading the bound config: `await app.container.resolve(MusicConfig)` → inspect `.backend`.
- Probe liveness with `curl {base_url}/health` before debugging code paths.
- For unit tests, use `AudioMusicModule.stub()` (pinned to `local-http`) and mock the backend protocol for hermetic assertions.

---

## Still Stuck?

- Review the config section: [Configuration](./CONFIGURATION.md)
- Trace the flow: [Architecture](./ARCHITECTURE.md)
- Check the [lexigram-multimedia-music](https://github.com/dbtinoy-/lexigram) repository and open an issue with the full error text, `MusicConfig.backend`, and your server's `/health` response.