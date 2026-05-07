# Quickstart

Get image and video super-resolution running in minutes.

---

## Install

```bash
uv add lexigram-multimedia-upscale
# Optional: local reference-server dependencies
uv add "lexigram-multimedia-upscale[real-esrgan-server]"  # Real-ESRGAN server (torch + realesrgan)
uv add "lexigram-multimedia-upscale[hat-server]"          # HAT server (torch + timm)
```

`lexigram-multimedia-upscale` depends on `lexigram`, `lexigram-contracts`, and `aiohttp` (installed automatically).

The package works **zero-config**: the default backend is `real-esrgan` talking to `http://localhost:5400`.

---

## Minimal Upscale

```python
import asyncio

from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.multimedia.upscale import UpscaleModule
from lexigram.contracts.multimedia import MediaAsset, UpscaleProvider, UpscaleRequest


@module(imports=[UpscaleModule.configure()])
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        upscale = await app.container.resolve(UpscaleProvider)

        asset = MediaAsset(
            mime_type="image/png",
            provider="local",
            bytes_data=b"<your png bytes>",
        )
        result = await upscale.upscale(UpscaleRequest(asset=asset, scale_factor=4))
        if result.is_ok():
            upscaled = result.unwrap()  # MediaAsset — upscaled image bytes
            print("upscaled:", upscaled.mime_type, len(upscaled.bytes_data or b""))


if __name__ == "__main__":
    asyncio.run(main())
```

With an `application.yaml`:

```yaml
multimedia:
  upscale:
    backend: "real-esrgan"
    real_esrgan_base_url: "http://localhost:5400"
```

Calling `UpscaleModule.configure()` with no arguments also works — `UpscaleConfig` defaults apply.

---

## What Just Happened

1. `UpscaleModule.configure()` creates a `DynamicModule` with an `UpscaleGenerationProvider`.
2. `Application.boot()` runs the provider lifecycle:
   - **register** — `UpscaleConfig` is bound in the container; the configured backend (`RealEsrganUpscaleProvider` or `HatUpscaleProvider`) is constructed and bound as `UpscaleProvider`; an `UpscaleTask` handler is bound; if a `VideoProcessor` is already resolvable, a `VideoUpscaleService` is bound too.
   - **boot** — a no-op: all HTTP happens per-request.
3. `upscale.upscale(UpscaleRequest(...))` base64-encodes the input, POSTs it to `<base_url>/upscale`, and returns `Ok(MediaAsset)` — or `Err(UpscaleError)` for transport/HTTP failures.

The reference server must be running on port `5400`:

```bash
lexigram-upscale-real-esrgan-serve
```

---

## Next Steps

- [Guide](./GUIDE.md) — mental model: assets, requests, backends, results
- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Configuration](./CONFIGURATION.md) — every config key and env-var override
- [Architecture](./ARCHITECTURE.md) — internal design and extension points