# How-To Guides

Task-oriented recipes for generating, storing, and job-queueing images.

---

## Generate an Image and Save It Locally

```python
import asyncio

from lexigram import Application
from lexigram.contracts.multimedia import ImageProvider, ImageRequest
from lexigram.multimedia.image import ImageModule


async def main() -> None:
    async with Application.boot(modules=[ImageModule.configure()]) as app:
        image = await app.container.resolve(ImageProvider)
        result = await image.generate(ImageRequest(prompt="a red rose on a table"))

        if result.is_ok():
            asset = result.unwrap()
            ext = asset.mime_type.split("/")[-1]
            with open(f"rose.{ext}", "wb") as f:
                f.write(asset.bytes_data)
        else:
            print(f"failed: {result.unwrap_err()}")


if __name__ == "__main__":
    asyncio.run(main())
```

The default `local-http` backend posts `{"prompt", "width", "height", "format"}`
to `http://localhost:5005/generate` and expects image bytes back. `asset.provider`
is `"local-http"` and `asset.mime_type` is whatever `Content-Type` the server
sent.

---

## Switch to OpenAI (DALL·E) with a Secrets-Backend Key

Configure the `openai` backend and resolve the key from the secret store by
name:

```python
from lexigram.multimedia.image import ImageModule
from lexigram.multimedia.image.config import ImageConfig


module = ImageModule.configure(
    config=ImageConfig(
        backend="openai",
        openai_model="dall-e-3",
        openai_api_key_secret_name="prod_openai_images",
    )
)
```

The secrets store must contain a secret named `prod_openai_images`. At runtime
the provider resolves it via `resolve_credential(...)`; if it resolves empty,
requests return `Err(ImageGenerationAuthenticationError)` on an HTTP 401.

Sizes are validated against the model before the request is sent — for
`dall-e-3` use `1024x1024`, `1024x1792`, or `1792x1024` (via `width`/`height`
or `extra={"aspect_ratio": "9:16"}`).

---

## Image-to-Image with Stability AI

```python
from lexigram.contracts.multimedia import ImageRequest

result = await image.generate(
    ImageRequest(
        prompt="convert the photo into a watercolor painting",
        width=1024,
        height=1024,
        format="png",
        reference_image=paint_me_bytes,        # source image bytes
        reference_mime_type="image/png",
        extra={"reference_strength": 0.5},     # how much of the original to keep
    )
)
```

When `reference_image` is set, `StabilityImageProvider` posts a multipart
`image-to-image` form to `/v2beta/stable-image/generate/sd3`. Larger
`reference_strength` keeps more of the source; `0.0` reproduces the prompt
almost exactly, `1.0` keeps the original.

---

## Run ComfyUI with a Custom Workflow

ComfyUI is a thin HTTP client: it submits a workflow, polls history, and
fetches the output image. Point it at a running server and optionally override
the bundled SDXL template with your own workflow JSON:

```yaml
multimedia_image:
  backend: "comfyui"
  comfyui_base_url: "http://localhost:8188"
  comfyui_checkpoint: "sd_xl_base_1.0.safetensors"
  comfyui_steps: 30
  comfyui_cfg_scale: 7.5
  comfyui_workflow_path: "/etc/lexigram/workflows/custom.json"
```

```python
result = await image.generate(
    ImageRequest(
        prompt="an astronaut riding a horse",
        extra={"negative_prompt": "blurry, low quality, deformed"},
    )
)
```

Workflow templates use `__PROMPT__`, `__NEGATIVE_PROMPT__`, `__WIDTH__`,
`__HEIGHT__`, `__CHECKPOINT__`, `__STEPS__`, `__CFG__`, and `__SEED__`
placeholders which `ComfyUiImageProvider._fill_workflow()` substitutes before
submitting to `/prompt`. Without `comfyui_workflow_path` the packaged
`default_sdxl.json` (SDXL checkpoint → KSampler → VAE → SaveImage) is used.

---

## Submit Generation as a Background Job

`ImageGenerationTask.run(params)` is the `lexigram-tasks` entry point — submit
plain-dict params and receive a JSON-serializable result dict:

```python
from lexigram.multimedia.image import ImageGenerationTask

params = {
    "prompt": "retro synthwave poster",
    "width": 1024,
    "height": 1024,
    "format": "png",
    "extra": {"negative_prompt": "text, watermark"},
}

task = ImageGenerationTask(backend=image_provider)  # usually container-resolved
result_dict = await task.run(params)
# -> {"provider": ..., "mime_type": ..., "bytes_data": ..., "uri": ..., "metadata": ...}
```

Note: `run()` returns a plain dict because the job result store JSON-serializes
`JobResult`. Under the `lexigram-multimedia` umbrella, the wrapper persists the
asset's bytes into `lexigram-storage` before this dict is constructed, so
`bytes_data` may be `null` and `uri` set instead.

---

## Check Provider Health at Runtime

```python
from lexigram.contracts.core.health import HealthStatus
from lexigram.multimedia.image import ImageGenerationProvider

provider = await app.container.resolve(ImageGenerationProvider)
status = await provider.health_check(timeout=5.0)  # HealthCheckResult
if status.status == HealthStatus.HEALTHY:
    print("image backend is up")
else:
    print("image backend is DEGRADED or UNHEALTHY")
```

`ImageGenerationProvider.health_check()`:

- `local-http` → `GET {local_http_base_url}/health`
- `comfyui` → `GET {comfyui_base_url}/system_stats`
- `openai` / `stability` → `HEALTHY` if the configured key resolved, else `DEGRADED`
- no backend registered yet → `UNHEALTHY`

---

## Notes

- Backends that cannot accept a reference image (ComfyUI, `local-http`) return
  `Err(ImageGenerationError(...))` — check the message, don't assume a network
  problem.
- `extra` keys are per-backend and silently ignored elsewhere; keep prompts
  conservative in prompt text instead of relying on `quality`/`watermark` for
  OpenAI-compatible gateways that may ignore them.
- `timeout` in `ImageConfig` applies per HTTP operation (post, poll, fetch) —
  a long ComfyUI render needs `comfyui_poll_interval` small and `timeout` large.