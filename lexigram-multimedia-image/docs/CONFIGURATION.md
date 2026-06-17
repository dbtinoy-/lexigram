# Configuration

All configuration options for `lexigram-multimedia-image`.

---

## Overview

`ImageConfig` extends `BaseConfig` (stdlib dataclasses, not pydantic) and
declares its YAML/env section via `config_section = "multimedia_image"`.
Loading follows the canonical `BaseConfig.from_yaml()` order — each later
source overrides the previous:

1. `application.yaml` values (base layer)
2. Profile overlay `application.{LEX_PROFILE}.yaml` (if set)
3. `LEX_*` environment variables

`ImageGenerationProvider` passes the section directly to the container:
`config_key = "multimedia_image"`. Under the `lexigram-multimedia` umbrella the
same keys nest as `multimedia: image:`. `Backend` is the only
switching decision — the rest of the fields are per-backend, and unused fields
are simply ignored.

## Basic Example

```yaml
# application.yaml
multimedia_image:
  backend: "stability"
  stability_api_key_secret_name: "my_stability_key"
  timeout: 90.0
```

```python
config = ImageConfig.from_yaml("application.yaml")  # section used automatically
assert config.backend == "stability"
```

Programmatic equivalent:

```python
from lexigram.multimedia.image import ImageModule
from lexigram.multimedia.image.config import ImageConfig

module = ImageModule.configure(
    config=ImageConfig(backend="openai", openai_model="dall-e-3")
)
```

## Options

All fields of `ImageConfig`:

| Option | Type | Default | Description |
|-------|------|--------|------------|
| `backend` | `Literal["local-http", "stability", "openai", "comfyui"]` | `"local-http"` | Which `ImageProvider` implementation to register |
| `local_http_base_url` | `str` | `"http://localhost:5005"` | Base URL of the self-hosted local generation server |
| `openai_api_key_secret_name` | `str` | `"openai_api_key"` | Name of the secret holding the OpenAI API key |
| `openai_model` | `str` | `"dall-e-3"` | OpenAI image model (`dall-e-3`, `dall-e-2`, or a gateway-routed model) |
| `openai_base_url` | `str` | `"https://api.openai.com"` | OpenAI-compatible base URL (also covers self-hosted gateways speaking `/v1/images/...`) |
| `stability_api_key_secret_name` | `str` | `"stability_api_key"` | Name of the secret holding the Stability AI API key |
| `comfyui_base_url` | `str` | `"http://localhost:8188"` | ComfyUI server URL |
| `comfyui_checkpoint` | `str` | `"sd_xl_base_1.0.safetensors"` | Checkpoint name injected into the workflow |
| `comfyui_workflow_path` | `str \| None` | `None` | Path to a custom workflow JSON; `None` uses the bundled SDXL template |
| `comfyui_steps` | `int` | `20` | KSampler steps in the workflow |
| `comfyui_cfg_scale` | `float` | `7.0` | KSampler CFG scale in the workflow |
| `comfyui_poll_interval` | `float` | `1.0` | Seconds between `/history/{prompt_id}` polls |
| `timeout` | `float` | `60.0` | Per-HTTP-operation timeout in seconds (post, poll, fetch) |

## Environment Variables

Prefix: `LEX_MULTIMEDIA__IMAGE__` (umbrella-layout YAML) or
`LEX_MULTIMEDIA_IMAGE__` (flat `multimedia_image` section). Field names map
directly, `__` separates nesting:

| Variable | Description |
|---------|------------|
| `LEX_MULTIMEDIA__IMAGE__BACKEND` | Backend selection |
| `LEX_MULTIMEDIA__IMAGE__LOCAL_HTTP_BASE_URL` | Local server URL |
| `LEX_MULTIMEDIA__IMAGE__OPENAI_API_KEY_SECRET_NAME` | OpenAI key secret name |
| `LEX_MULTIMEDIA__IMAGE__OPENAI_MODEL` | OpenAI model |
| `LEX_MULTIMEDIA__IMAGE__OPENAI_BASE_URL` | OpenAI-compatible base URL |
| `LEX_MULTIMEDIA__IMAGE__STABILITY_API_KEY_SECRET_NAME` | Stability key secret name |
| `LEX_MULTIMEDIA__IMAGE__COMFYUI_BASE_URL` | ComfyUI URL |
| `LEX_MULTIMEDIA__IMAGE__COMFYUI_CHECKPOINT` | ComfyUI checkpoint |
| `LEX_MULTIMEDIA__IMAGE__COMFYUI_WORKFLOW_PATH` | Custom workflow JSON path |
| `LEX_MULTIMEDIA__IMAGE__COMFYUI_STEPS` | Sampling steps |
| `LEX_MULTIMEDIA__IMAGE__COMFYUI_CFG_SCALE` | CFG scale |
| `LEX_MULTIMEDIA__IMAGE__COMFYUI_POLL_INTERVAL` | Poll interval seconds |
| `LEX_MULTIMEDIA__IMAGE__TIMEOUT` | Request timeout seconds |

Example:

```bash
export LEX_MULTIMEDIA__IMAGE__BACKEND=openai
export LEX_MULTIMEDIA__IMAGE__OPENAI_MODEL=dall-e-3
export LEX_MULTIMEDIA__IMAGE__TIMEOUT=120
```

## Advanced Configuration

### Secrets-Backed Keys (recommended for owned keys)

Config values are stored in the env/YAML only by default. For a key you own,
store it in the secrets backend and configure the provider
(`AsyncSecretStoreProtocol` in the container) — `ImageGenerationProvider`
resolves it via `resolve_credential(secret_store, ...)` at register time:

```python
# container already has AsyncSecretStoreProtocol registered
module = ImageModule.configure(
    config=ImageConfig(
        backend="stability",
        stability_api_key_secret_name="lex_stability",
    ),
)
```

`to_safe_dict()` redacts any field matching secret patterns, so logs never
leak keys.

### Resilience Wrapping

Backends accept optional `RetryPolicyProtocol` / `CircuitBreakerProtocol`
instances. Under DI these resolve automatically when the corresponding
protocols are registered — every HTTP call is then wrapped in
`retry.execute(...)` / `circuit_breaker.call(...)`. Direct construction works
too:

```python
from lexigram.multimedia.image.providers import OpenAIImageProvider

backend = OpenAIImageProvider(
    api_key="sk-...",
    model="dall-e-3",
    base_url="https://api.openai.com",
    timeout=60.0,
    retry=my_retry_policy,
    circuit_breaker=my_circuit_breaker,
)
```

### Profile-Based Overlays

```bash
export LEX_PROFILE=production
```

with `application.production.yaml` containing only the fields that differ
(e.g. `backend: "openai"`) — `ImageConfig.from_env_profile()` applies the
overlay and then env vars on top of the base file.

## Best Practices

- Keep `ImageConfig` minimal — only the fields for the backend you run.
- Prefer environment variables for per-deployment overrides (backends, URLs).
- Never hardcode API keys in YAML — reference secret names and resolve via the
  secrets backend.
- Keep `comfyui_poll_interval` small relative to `timeout` so long renders have
  headroom to complete.
- Use `ImageModule.stub()` (pinned `local-http`) in tests instead of mocking
  away the module.