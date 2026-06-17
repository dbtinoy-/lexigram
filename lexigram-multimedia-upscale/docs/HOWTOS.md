# How-To Guides

Task-oriented recipes for `lexigram-multimedia-upscale`.

---

## Upscale a Byte-Backed Image (2x or 4x)

```python
from lexigram.contracts.multimedia import MediaAsset, UpscaleRequest

result = await upscale_provider.upscale(
    UpscaleRequest(
        asset=MediaAsset(
            mime_type="image/png",
            provider="upload",
            bytes_data=png_bytes,
        ),
        scale_factor=2,
    )
)
if result.is_ok():
    upscaled = result.unwrap()
    with open("output.png", "wb") as f:
        f.write(upscaled.bytes_data or b"")
```

`scale_factor` is typed `Literal[2, 4]` and defaults to `4`.

---

## Upscale an Image Referenced by URI

```python
result = await upscale_provider.upscale(
    UpscaleRequest(
        asset=MediaAsset(
            mime_type="image/jpeg",
            provider="object-store",
            uri="https://cdn.example.com/photo.jpg",
        ),
        scale_factor=4,
    )
)
```

The provider downloads the URI via `resolve_asset_bytes()` before POSTing.

---

## Switch the Backend to HAT

```python
from lexigram.multimedia.upscale import UpscaleModule
from lexigram.multimedia.upscale.config import UpscaleConfig

module = UpscaleModule.configure(config=UpscaleConfig(backend="hat"))
```

Or via YAML / env:

```yaml
multimedia:
  upscale:
    backend: "hat"
```

```bash
export LEX_MULTIMEDIA__UPSCALE__BACKEND=hat
lexigram-upscale-hat-serve   # start the HAT reference server on :5401
```

---

## Upscale a Whole Video

Requires a `VideoProcessor` in the container — install `lexigram-multimedia-video` and register its module alongside:

```python
from lexigram.contracts.multimedia import MediaAsset
from lexigram.multimedia.upscale import VideoUpscaleService

video = await app.container.resolve(VideoUpscaleService)
result = await video.upscale_video(
    MediaAsset(mime_type="video/mp4", provider="local", bytes_data=mp4_bytes),
    scale_factor=2,  # Literal[2, 4]
)
if result.is_ok():
    out = result.unwrap()  # new MediaAsset ("video/mp4", provider="ffmpeg")
```

The service extracts frames with `VideoProcessor.extract_frames()`, upscales each with the single-image `UpscaleProvider`, and reassembles with `assemble_frames(fps=...)` using the source fps recorded in frame `metadata["source_fps"]` (default `30.0`).

---

## Submit an Upscale as an Async Job

```python
task = await app.container.resolve(UpscaleTask)
job_params = {
    "asset": {
        "mime_type": "image/png",
        "provider": "upload",
        "uri": "https://cdn.example.com/photo.png",
    },
    "scale_factor": 4,
    "extra": {"pipeline": "catalog"},
}
result_dict = await task.run(job_params)

# result_dict (JSON-serializable):
# {provider, mime_type, bytes_data, uri, metadata}
```

Errors from the backend are raised (`result.unwrap_err()`), so the job fails loudly rather than storing a partial result.

---

## Check Server Health

```python
provider = next(p for p in app.providers if p.name == "upscale")
health = await provider.health_check(timeout=2.0)
print(health.status)  # HealthStatus.HEALTHY | DEGRADED | UNHEALTHY
```

Providers live on the application orchestrator, not in the container — look them up by their `name` ("upscale") via `app.providers`.

`health_check()` GETs `<base_url>/health`; a `200` means `HEALTHY`, any other status or a connection/OSError failure means `DEGRADED`. With no backend registered it returns `UNHEALTHY`.

---

## Add Retries and a Circuit Breaker

Register resilience primitives in the container and the provider wires them into the backend automatically:

```python
# In a custom provider's register():
container.singleton(RetryPolicyProtocol, retry_policy)
container.singleton(CircuitBreakerProtocol, circuit_breaker)

# UpscaleGenerationProvider.register() resolves both and passes them to
# RealEsrganUpscaleProvider / HatUpscaleProvider constructors.
```

When both are present the call path is `retry.execute(circuit_breaker.call, self._post, payload)`.

---

## Run the Reference Server Manually

```bash
lexigram-upscale-real-esrgan-serve   # binds :5400
lexigram-upscale-hat-serve           # binds :5401
```

Both are aiohttp apps: `POST /upscale` (base64 `image_bytes` + `scale_factor`, returns raw PNG bytes) and `GET /health`. Models load **once** in `on_startup()` and are reused across requests.

---

## Notes

- Payloads are base64-inlined JSON — very large images inflate the request; keep inputs sane for your server's request limits.
- A non-200 response surfaces as `Err(UpscaleError)` with the server's text body.
- The `real-esrgan-server` / `hat-server` extras are empty in `pyproject.toml` — install `torch` (and `realesrgan` or the HAT package) yourself in the server venv.
- `ProviderNotInstalledError` is raised at registration time if `UpscaleConfig.backend` is neither `real-esrgan` nor `hat`.