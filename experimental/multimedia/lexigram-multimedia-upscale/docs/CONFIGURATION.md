# Configuration

Configuration options for `lexigram-multimedia-upscale`.

---

## Overview

Configuration lives on `UpscaleConfig` (a `lexigram.config.BaseConfig` subclass). As a subsystem of the `lexigram-multimedia` umbrella, it is nested under the `multimedia:` key in `application.yaml` with environment-variable prefix `LEX_MULTIMEDIA__UPSCALE__`. Alternatively, pass an `UpscaleConfig` directly to `UpscaleModule.configure(...)`.

| Config class | `config_section` | Provider |
|--------------|------------------|----------|
| `UpscaleConfig` | `"multimedia_upscale"` | consumed by `UpscaleGenerationProvider` (provider `config_key` = `"multimedia_upscale"`) |

### Zero-config default

Calling `UpscaleModule.configure()` with no arguments produces `UpscaleConfig(backend="real-esrgan")` — super-resolution against a reference server at `http://localhost:5400`.

---

## Basic Example

```yaml
multimedia:
  upscale:
    backend: "hat"                     # real-esrgan | hat
    real_esrgan_base_url: "http://localhost:5400"
    hat_base_url: "http://localhost:5401"
    timeout: 30.0
```

```python
from lexigram.multimedia.upscale import UpscaleModule
from lexigram.multimedia.upscale.config import UpscaleConfig

UpscaleModule.configure(
    config=UpscaleConfig(backend="hat", hat_base_url="http://10.0.0.5:5401")
)
```

---

## Options

### `UpscaleConfig`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `backend` | `Literal["real-esrgan", "hat"]` | `"real-esrgan"` | Which super-resolution backend to build at registration time |
| `real_esrgan_base_url` | `str` | `"http://localhost:5400"` | Base URL of the Real-ESRGAN reference server |
| `hat_base_url` | `str` | `"http://localhost:5401"` | Base URL of the HAT reference server |
| `timeout` | `float` | `30.0` | Per-request HTTP timeout in seconds (aiohttp `ClientTimeout.total`) |

The upscale **factor is not config-state**: pass it per request via `UpscaleRequest.scale_factor` (`Literal[2, 4]`, default `4`).

### Backend constructor mapping

The provider forwards config into the backend constructors in `UpscaleGenerationProvider.register()`:

| `backend` | Class constructed | Args |
|-----------|-------------------|------|
| `"real-esrgan"` | `RealEsrganUpscaleProvider` | `base_url=real_esrgan_base_url`, `timeout`, `retry`, `circuit_breaker` |
| `"hat"` | `HatUpscaleProvider` | `base_url=hat_base_url`, `timeout`, `retry`, `circuit_breaker` |
| anything else | raises `ProviderNotInstalledError` | — |

`retry` / `circuit_breaker` come from optional `RetryPolicyProtocol` / `CircuitBreakerProtocol` bindings in the container.

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `LEX_MULTIMEDIA__UPSCALE__BACKEND` | Override `backend` |
| `LEX_MULTIMEDIA__UPSCALE__REAL_ESRGAN_BASE_URL` | Override `real_esrgan_base_url` |
| `LEX_MULTIMEDIA__UPSCALE__HAT_BASE_URL` | Override `hat_base_url` |
| `LEX_MULTIMEDIA__UPSCALE__TIMEOUT` | Override `timeout` |

```bash
export LEX_PROFILE=production
export LEX_MULTIMEDIA__UPSCALE__BACKEND=hat
export LEX_MULTIMEDIA__UPSCALE__HAT_BASE_URL=http://10.0.0.5:5401
```

---

## Advanced Configuration

### Testing with `stub()`

```python
module = UpscaleModule.stub()
# Equivalent to configure(config=UpscaleConfig(backend="real-esrgan"))
# — useful in test suites; the module is real, the default backend is pinned.
```

### Wiring through an umbrella module

```python
@module(imports=[UpscaleModule.configure()])
class AppModule(Module):
    pass
```

The umbrella `lexigram-multimedia` orchestrator may also import this subsystem by entry point `lexigram.multimedia.subsystems` (`upscale`) or `lexigram.multimedia.modules` (`upscale`) — no config needed in that case beyond the `multimedia: upscale:` YAML section.

### Optional cross-package wiring

`VideoUpscaleService` only registers when a `VideoProcessor` is resolvable in the container (provided by `lexigram-multimedia-video` when `ffmpeg` is on `PATH`). No upscale-side flag controls this — presence of the processor is the switch.

---

## Best Practices

- ✅ Prefer environment variables / YAML for backend choice; keep secrets out of config entirely.
- ✅ Use per-request `scale_factor` rather than forking config per scale.
- ✅ Point `*_base_url` at machines that run `lexigram-upscale-*-serve`.
- ❌ Don't hardcode model weights or server code in the application — the reference servers are separate processes.
- ❌ Don't expect `backend="real-esrgan"` to work without a server listening on the configured port.