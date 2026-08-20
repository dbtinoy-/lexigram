# Troubleshooting

Common issues and fixes for `lexigram-multimedia-image`.

---

## Problem: `ProviderNotInstalledError` at boot — unknown backend

**Error:**

```
ProviderNotInstalledError: Unknown or unimplemented image backend: 'foo'
```

**Cause:** `ImageConfig.backend` is not one of the four implemented values, or
the provider has no branch for it.

**Solution:** Use an implemented backend string:

```python
from lexigram.multimedia.image.config import ImageConfig

config = ImageConfig(backend="local-http")  # or "stability" | "openai" | "comfyui"
```

---

## Problem: `local-http` request hangs then fails

**Error:**

```
ImageGenerationError: local-http image request failed: ...
ImageTimeoutError: ...
```

**Cause:** No server is listening at `local_http_base_url` (default
`http://localhost:5005`), or the server does not implement `POST /generate`.

**Solution:** Start/point the server at the right URL and confirm the endpoint:

```bash
curl -X POST http://localhost:5005/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"test","width":512,"height":512,"format":"png"}' -o out.png
```

Bring up a server on the expected port, or change the URL:

```yaml
multimedia_image:
  backend: "local-http"
  local_http_base_url: "http://127.0.0.1:5005"
```

---

## Problem: OpenAI/Stability returns 401 authentication error

**Error:**

```
ImageGenerationAuthenticationError: OpenAI rejected the API key
ImageGenerationAuthenticationError: Stability AI rejected the API key
```

**Cause:** The API key resolved empty or wrong. `ImageGenerationProvider`
resolved the key by `openai_api_key_secret_name` / `stability_api_key_secret_name`
via the secrets store; with no secret store — or a missing/incorrect secret — the
key is `""`.

**Solution:**

1. Confirm the secret exists in the secrets backend under the configured name.
2. Point config at the correct secret name:
   ```python
   config = ImageConfig(backend="openai", openai_api_key_secret_name="prod_openai_images")
   ```
3. Verify the key is live by testing the API directly with `curl` and the same
   `Authorization: Bearer` value.

Note the app still boots with an empty key — the failure surfaces when the
first request runs.

---

## Problem: `ImageTimeoutError` — ComfyUI prompt never completes

**Error:**

```
ImageTimeoutError: ComfyUI prompt <id> did not complete in time
```

**Cause:** The render took longer than `timeout` (default `60.0`) — heavy
checkpoints, high `comfyui_steps`, or a slow GPU. Every poll at
`comfyui_poll_interval` adds latency.

**Solution:** Split the budget: reduce `comfyui_poll_interval` (faster
feedback) and raise `timeout`.

```yaml
multimedia_image:
  backend: "comfyui"
  comfyui_poll_interval: 0.5
  timeout: 300.0
```

---

## Problem: ComfyUI returns a failure the provider never treats as an error

**Error:** Generation returns image results, or an unexpected
`ImageGenerationError` about execution, but nothing points at the real cause.

**Cause:** ComfyUI reports some errors only via a `"execution_error"` entry in
`status["messages"]`, not via `status_str`. The provider checks both, so an
unusual custom workflow may need review.

**Solution:** Inspect the workflow + server logs for the actual node failure and
either fix the workflow JSON or confirm the checkpoint name:

```
lexigram.multimedia.image.providers.comfyui  | ...
```

Verify `comfyui_checkpoint` matches an installed checkpoint, and that
`comfyui_workflow_path` (if set) is valid JSON using the `__*__` placeholders.

---

## Problem: OpenAI rejects the requested size

**Error:**

```
ImageGenerationError: dall-e-3 does not support size '512x512'; supported sizes: [...]
```

**Cause:** Width/height (or `extra["size"]` / `extra["aspect_ratio"]`) don't
match the model's supported set. `dall-e-3` only supports `1024x1024`,
`1024x1792`, `1792x1024`; `dall-e-2` supports `256x256`, `512x512`, `1024x1024`.

**Solution:** Use a supported size for the model, or choose `dall-e-2` for
smaller outputs:

```python
request = ImageRequest(
    prompt="logo design",
    extra={"aspect_ratio": "16:9"},          # → 1792x1024 for dall-e-3
)
```

---

## Debug Tips

- Enable debug logging to confirm which backend registered:
  `ImageGenerationProvider` logs `image_registered` with the backend name.
- Call `provider.health_check(timeout=5.0)` before a real request — it reports
  `DEGRADED` for unreachable HTTP backends without burning a generation.
- Check the `Err` payload's `.cause` — backends attach the underlying
  `aiohttp`/`TimeoutError`.
- In tests, use `ImageModule.stub()` (pinned `local-http`) to avoid network and
  API keys entirely.

---

## Still Stuck?

- Re-read the fields in [Configuration](./CONFIGURATION.md) — a wrong
  backend URL is the most common cause of request failures.
- Confirm the backend is actually expected to reach a network: `stability`,
  `openai`, and `comfyui` all require a live endpoint or key.
- Open an issue at
  https://github.com/dbtinoy-/lexigram/issues