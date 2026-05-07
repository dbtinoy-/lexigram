# Guide

Understand and use `lexigram-multimedia-image` effectively.

---

## Overview

`lexigram-multimedia-image` generates still images from a text prompt inside the
Lexigram framework. It is a backend-selection layer: one `ImageConfig.backend`
field switches between four implementations of the same `ImageProvider`
protocol, and one `ImageGenerationProvider` registers the winner in the DI
container. Everything downstream — your services, the `ImageGenerationTask`
job handler, the umbrella `lexigram-multimedia` module — talks to
`ImageProvider` and never sees which backend produced the image.

| Backend | Config value | What it calls | Costs a key? |
|---------|--------------|---------------|--------------|
| Local HTTP | `local-http` | `POST /generate` on a self-hosted server | No |
| Stability AI | `stability` | `api.stability.ai/v2beta/stable-image/generate/sd3` | Yes |
| OpenAI | `openai` | `/v1/images/generations` or `/v1/images/edits` | Yes |
| ComfyUI | `comfyui` | Local ComfyUI `/prompt`, `/history`, `/view` | No (GPU + model) |

The default backend needs no API key and no GPU, so the package is usable out
of the box.

---

## Core Concepts

- **`ImageProvider`** — the structural contract
  (`lexigram.contracts.multimedia.protocols`). One method:
  `async generate(request: ImageRequest) -> Result[MediaAsset, MultimediaError]`.
  All four backends match it via structural typing; there is no shared base
  class.
- **`ImageRequest`** — the frozen request value: `prompt`, `width` (1024),
  `height` (1024), `format` (`"png"`), optional `reference_image` /
  `reference_mime_type` for image-to-image, and a free-form `extra` dict for
  backend-specific knobs.
- **`MediaAsset`** — the frozen result value carrying `mime_type`, `provider`,
  and either `bytes_data` or `uri` (check `has_bytes` / `has_uri`). Backends
  return raw bytes; the umbrella persists them into storage.
- **`Result[T, E]` semantics** — expected failures (bad prompt, server down,
  rejected key) come back as `Err(ImageGenerationError)`. Infrastructure
  failures that happen *inside* the call (`aiohttp.ClientError`,
  `TimeoutError`) are converted to `Err`, never raised. Catch
  `ImageGenerationAuthenticationError` / `ImageTimeoutError` only for special
  handling — `ImageGenerationError` covers the rest.
- **`ImageGenerationProvider`** — the DI provider. Selects the backend from
  `ImageConfig.backend`, resolves API keys from the secrets store by name, and
  binds `ImageConfig`, `ImageProvider`, and `ImageGenerationTask` as
  singletons.
- **`ImageGenerationTask`** — the `lexigram-tasks` bridge. Its `run(params)`
  builds an `ImageRequest` from plain dict params and returns a JSON-serializable
  dict (never raw bytes) so job results can be stored.

---

## Typical Usage

```python
from lexigram import Application
from lexigram.contracts.multimedia import ImageProvider, ImageRequest
from lexigram.multimedia.image import ImageModule


async def generate_hero() -> None:
    async with Application.boot(modules=[ImageModule.configure()]) as app:
        image = await app.container.resolve(ImageProvider)
        result = await image.generate(
            ImageRequest(
                prompt="futuristic city skyline at dusk, cinematic lighting",
                width=1792,
                height=1024,
                format="png",
            )
        )
        if result.is_ok():
            asset = result.unwrap()
            # asset.mime_type, asset.provider, asset.bytes_data
            persist(asset.bytes_data, asset.mime_type if asset.has_bytes else asset.uri)
        else:
            logger.warning("generation_failed", error=str(result.unwrap_err()))
```

What is happening:

- The service depends on the `ImageProvider` **protocol**, not a concrete
  backend — swap `backend` in config, nothing else changes.
- `generate()` is fully async, so it composes with the rest of the framework
  (routes, tasks, queues) without blocking the event loop.
- The `Result` is handled explicitly — `is_ok()` before `unwrap()`, and the
  `Err` branch gets the domain error value to log or surface.

---

## Common Patterns

### Pattern: Image-to-Image Conditioning

`ImageRequest.reference_image` activates image-to-image on backends that
support it. OpenAI allows it only on `dall-e-2`; Stability takes a
`reference_strength` (default 0.65); ComfyUI and `local-http` reject it with an
`Err`.

```python
request = ImageRequest(
    prompt="same portrait, now in a cyberpunk setting",
    width=1024,
    height=1024,
    reference_image=source_bytes,          # raw PNG bytes
    reference_mime_type="image/png",
    extra={"reference_strength": 0.8},     # stability backend only
)
```

### Pattern: Backend-Specific Knobs via `extra`

Each backend reads its own keys and ignores the rest:

| Backend | `extra` keys |
|---------|--------------|
| OpenAI | `size`, `aspect_ratio` (`1:1`/`9:16`/`16:9`), `quality`, `output_format`, `watermark` |
| Stability | `reference_strength` |
| ComfyUI | `negative_prompt` |

### Pattern: Unwrap with a Fallback Stub

In tests or demos, keep the module real but pinned to the offline backend:

```python
module = ImageModule.stub()  # ImageConfig(backend="local-http")
```

`stub()` returns a genuine `ImageGenerationProvider` — safe for integration
tests that only assert the container wiring.

---

## Integration

- **`lexigram-multimedia` umbrella** — `MultimediaModule` auto-discovers this
  package through the `lexigram.multimedia.subsystems` / `lexigram.multimedia.modules`
  entry points, and wraps the task handler to persist bytes into
  `lexigram-storage` before the job result dict is built. In the umbrella your
  YAML nests the config under `multimedia: image:`.
- **`lexigram-tasks`** — `ImageGenerationTask.run()` is the submit-path entry
  point; it raises the backend error if generation fails, which the task
  system records on the job.
- **Secrets backend** — keys are resolved by name via
  `AsyncSecretStoreProtocol` (`lexigram.di.provider_utils.resolve_credential`).
  No secret store, no key: OpenAI/Stability requests will 401 at runtime.
- **Resilience** — if the container has `RetryPolicyProtocol` and/or
  `CircuitBreakerProtocol` registered, backends execute requests through them
  automatically (see `RetryPolicyProtocol.execute` / `CircuitBreakerProtocol.call`).
- **Health checks** — `ImageGenerationProvider.health_check()` reports
  `HealthStatus.HEALTHY`/`DEGRADED` by probing `/health` (local-http),
  `/system_stats` (ComfyUI), or the credential flag (OpenAI/Stability).

---

## Best Practices

- ✅ Depend on `ImageProvider` in your services — never import a concrete backend.
- ✅ Treat expected failures as `Result` values: check `is_ok()`/`is_err()`, use
  `unwrap_or()` for fallbacks.
- ✅ Use `local-http` and `ImageModule.stub()` in tests; no API keys, no network.
- ✅ Store API keys in the secrets backend and reference them by name in config —
  never paste keys into `application.yaml` (`to_safe_dict()` redacts secret-named
  fields).
- ✅ Set `negative_prompt` via `extra` on ComfyUI requests to steer generations.
- ❌ Don't call `result.unwrap()` before checking `is_ok()` — an error is an
  expected domain value.
- ❌ Don't request unsupported sizes — `dall-e-3` only accepts `1024x1024`,
  `1024x1792`, `1792x1024`; the provider rejects others with an `Err`.
- ❌ Don't treat OpenAI/Stability as offline-safe — without a resolved key the
  backend registers (so the app boots) but every request fails with
  `ImageGenerationAuthenticationError`.

---

## Next Steps

- [How-Tos](./HOWTOS.md) — specific task recipes
- [Configuration](./CONFIGURATION.md) — every config key
- [Architecture](./ARCHITECTURE.md) — internal design and extension points