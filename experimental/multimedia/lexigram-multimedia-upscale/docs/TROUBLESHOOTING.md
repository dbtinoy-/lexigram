# Troubleshooting

Common issues with `lexigram-multimedia-upscale` and how to fix them.

---

## `ProviderNotInstalledError: Unknown or unimplemented upscale backend`

**Cause:** `UpscaleConfig.backend` is neither `real-esrgan` nor `hat`.

**Fix:** Use a valid backend:

```python
from lexigram.multimedia.upscale.config import UpscaleConfig

UpscaleConfig(backend="real-esrgan")  # or "hat"
```

```yaml
multimedia:
  upscale:
    backend: "hat"
```

---

## Upscale always returns a connection-style error

**Error:** `UpscaleError: Real-ESRGAN request failed: <aiohttp ClientError>` or `HAT request failed: ...`, or the provider reports `DEGRADED`.

**Cause:** The reference server is not running on the configured base URL, or a firewall/port mismatch.

**Fix:** Start the server and confirm the port:

```bash
lexigram-upscale-real-esrgan-serve   # :5400 (backend real-esrgan)
lexigram-upscale-hat-serve           # :5401 (backend hat)
curl -s http://localhost:5400/health   # -> {"status":"ok"}
```

Check that `real_esrgan_base_url` / `hat_base_url` in config match the running server.

---

## `UpscaleError: ... server returned <status>` with a non-200

**Cause:** The server rejected the request (e.g. bad payload, model still loading, upstream error).

**Fix:** Inspect the echoed body:

```python
result = await upscale.upscale(UpscaleRequest(asset=asset, scale_factor=4))
if result.is_err():
    print(result.unwrap_err())  # includes the server's text body
```

The reference servers return `{"status":"loading"}` from `/health` until the model finishes loading on startup — wait for the model before first use.

---

## `HealthStatus.DEGRADED` from `health_check()`

**Cause:** `GET <base_url>/health` did not return `200` (connection error, timeout, or non-200 status).

**Fix:**

- Ensure the server is up: `curl -s http://localhost:5400/health`.
- Give model startup time (models load once in `on_startup`).
- Raise the health timeout: `await provider.health_check(timeout=10.0)`.

`UNHEALTHY` specifically means no backend was registered (e.g. provider never ran `register()`).

---

## HAT reference server fails to import / start

**Cause:** HAT has no canonical single PyPI package — model weights and inference code are commonly vendored from the paper authors' repo, so a plain install may not provide `HatSuperResolutionModel`.

**Fix:** Install the actual HAT distribution your server venv uses and verify the inference entrypoint against it:

```bash
pip install torch timm lexigram-multimedia-upscale
# install the real HAT package your deployment vendored
lexigram-upscale-hat-serve
```

See the server module docstring note for the same caveat.

---

## `VideoUpscaleService` is not resolvable from the container

**Error:** Resolution error for `VideoUpscaleService`.

**Cause:** `VideoUpscaleService` only registers when a `VideoProcessor` is present in the container. `lexigram-multimedia-video` registers its `FFmpegVideoProcessor` only when `ffmpeg` is found on `PATH`.

**Fix:** Install `lexigram-multimedia-video`, register `VideoModule`, and confirm `ffmpeg` is installed:

```bash
uv add lexigram-multimedia-video
which ffmpeg   # must resolve
```

```python
@module(imports=[
    VideoModule.configure(),
    UpscaleModule.configure(),
])
class AppModule(Module):
    pass
```

---

## Very large input images time out or are rejected

**Cause:** Inputs are base64-inlined into a JSON POST body; oversized payloads can exceed server request limits or the configured `timeout`.

**Fix:**

- Raise `UpscaleConfig.timeout`.
- Downscale/re-encode the source before upscaling.
- Prefer serving the input over `asset.uri` (still resolved by the provider) rather than inlining huge byte blobs.

---

## Upscale output looks blurry or the factor seems ignored

**Cause:** `scale_factor` is per-request (`UpscaleRequest.scale_factor`); it is not read from config. The server defaults to `4` when omitted.

**Fix:** Pass the factor explicitly on each request:

```python
UpscaleRequest(asset=asset, scale_factor=2)  # reads "2", even if others use 4
```

---

## Debug Tips

- Enable logging to see registration details:

```bash
export LOG_LEVEL=DEBUG
```

  The provider logs `upscale_registered` with the active backend.
- Validate the container after boot:

```python
upscale = await app.container.resolve(UpscaleProvider)
print(type(upscale).__name__)  # RealEsrganUpscaleProvider | HatUpscaleProvider
```

- Check health directly rather than guessing which engine is active:

```python
prov = next(p for p in app.providers if p.name == "upscale")
print(await prov.health_check())
```

---

## Still Stuck?

- Re-read [Configuration](./CONFIGURATION.md) and confirm base URLs match your servers.
- Exercise the wire by hand against a reference server with `curl`.
- Open an issue at [lexigram](https://github.com/dbtinoy-/lexigram/issues) with the provider, backend, and the exact `UpscaleError` message.