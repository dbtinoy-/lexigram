# lexigram-multimedia-interpolate

Video frame-rate interpolation for the Lexigram Framework — a local RIFE reference-server backend that doubles or quadruples a clip's frame rate by synthesizing midpoint frames.

---

## Overview

`lexigram-multimedia-interpolate` synthesizes intermediate frames between two input frames (or between frames of a video) using a RIFE reference server, and registers a `VideoInterpolationService` for frame-level video interpolation when a `VideoProcessor` is available in the container.

> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)

## Install

```bash
uv add lexigram-multimedia-interpolate
# Optional extras
uv add "lexigram-multimedia-interpolate[rife-server]"  # RIFE server deps (torch)
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.multimedia.interpolate import InterpolationModule
from lexigram.contracts.multimedia.protocols import InterpolationProvider
from lexigram.contracts.multimedia.types import InterpolationRequest, MediaAsset


@module(imports=[InterpolationModule.configure()])
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        interpolate = await app.container.resolve(InterpolationProvider)
        frame_a = MediaAsset(mime_type="image/png", provider="local", bytes_data=b"<png>")
        frame_b = MediaAsset(mime_type="image/png", provider="local", bytes_data=b"<png>")
        result = await interpolate.interpolate(
            InterpolationRequest(frame_a=frame_a, frame_b=frame_b)
        )
        if result.is_ok():
            midframe = result.unwrap()  # MediaAsset — synthesized midpoint frame


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

## Configuration

> **Zero-config usage:** Call `InterpolationModule.configure()` with no arguments to use the `rife` backend at `http://localhost:5500`.

### Option 1 — YAML file

```yaml
# application.yaml
multimedia:
  interpolate:
    backend: "rife"
    default_factor: 4
```

### Option 2 — Profiles + Environment Variables

```bash
export LEX_PROFILE=production
export LEX_MULTIMEDIA__INTERPOLATE__BACKEND=rife
export LEX_MULTIMEDIA__INTERPOLATE__DEFAULT_FACTOR=4
```

### Option 3 — Python

```python
from lexigram.multimedia.interpolate import InterpolationModule
from lexigram.multimedia.interpolate.config import InterpolationConfig

InterpolationModule.configure(
    config=InterpolationConfig(default_factor=4)
)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `backend` | `"rife"` | `LEX_MULTIMEDIA__INTERPOLATE__BACKEND` | `rife` |
| `rife_base_url` | `"http://localhost:5500"` | `LEX_MULTIMEDIA__INTERPOLATE__RIFE_BASE_URL` | RIFE server URL |
| `default_factor` | `2` | `LEX_MULTIMEDIA__INTERPOLATE__DEFAULT_FACTOR` | Interpolation factor (2 or 4) |
| `timeout` | `15.0` | `LEX_MULTIMEDIA__INTERPOLATE__TIMEOUT` | Request timeout in seconds |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `InterpolationModule.configure(config)` | Configure with explicit interpolation config |
| `InterpolationModule.stub()` | No-op module for unit testing |

## Key Features

- **RIFE backend** — state-of-the-art frame interpolation via a local reference server
- **Video interpolation** — `VideoInterpolationService` for frame-level video interpolation (when `VideoProcessor` is available)
- **Reference server** — `lexigram-interpolate-rife-serve` console script runs the RIFE model server
- **Result-based** — `interpolate() -> Result[MediaAsset, MultimediaError]`; errors are domain values, not exceptions

## Testing

```python
from lexigram import Application
from lexigram.multimedia.interpolate import InterpolationModule

async def test_boot():
    async with Application.boot(modules=[InterpolationModule.stub()]) as app:
        assert app.container is not None
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/multimedia/interpolate/module.py` | `InterpolationModule.configure()` and `.stub()` |
| `src/lexigram/multimedia/interpolate/config.py` | `InterpolationConfig` |
| `src/lexigram/multimedia/interpolate/di/provider.py` | `InterpolationGenerationProvider` — registers `InterpolationProvider`, wires task handlers |
| `src/lexigram/multimedia/interpolate/providers/` | Backend implementations (`rife`) |
| `src/lexigram/multimedia/interpolate/servers/` | Reference-server entry point (`lexigram-interpolate-rife-serve`) |
| `src/lexigram/multimedia/interpolate/video_interpolation_service.py` | `VideoInterpolationService` — frame-level video interpolation |
| `src/lexigram/multimedia/interpolate/tasks.py` | Background interpolation task handlers |
| `src/lexigram/multimedia/interpolate/exceptions.py` | `InterpolationTimeoutError` (extends `MultimediaError`) |
