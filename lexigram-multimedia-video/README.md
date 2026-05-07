# lexigram-multimedia-video

Video generation and processing for the Lexigram Framework — local and API-based backends (`local-http`, `runway`, `openai`, `wan22`, `cogvideox`, `svd`, `comfyui`) plus an ffmpeg-backed `VideoProcessor`.

---

## Overview

`lexigram-multimedia-video` generates video from a text prompt and edits existing clips. The default backend calls a local HTTP reference server (`http://localhost:5004`) so the package works out of the box with no API keys; hosted backends (Runway, OpenAI), ComfyUI workflows, and local reference servers (Wan2.2, CogVideoX, SVD) are selectable via config. A built-in `VideoProcessor` provides ffmpeg-based editing (trim, concat, overlay, transcode, subtitles, GIF, and more).

> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)

## Install

```bash
uv add lexigram-multimedia-video
# Optional extras
uv add "lexigram-multimedia-video[runway]"            # Runway API
uv add "lexigram-multimedia-video[openai]"            # OpenAI Sora API
uv add "lexigram-multimedia-video[wan22-server]"      # local Wan2.2 server (torch)
uv add "lexigram-multimedia-video[cogvideox-server]"  # local CogVideoX server (torch)
uv add "lexigram-multimedia-video[svd-server]"        # local SVD server (torch)
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.multimedia.video import VideoModule
from lexigram.contracts.multimedia import VideoProvider, VideoRequest


@module(imports=[VideoModule.configure()])
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        video = await app.container.resolve(VideoProvider)
        result = await video.generate(VideoRequest(prompt="a drone flying over mountains"))
        if result.is_ok():
            asset = result.unwrap()  # MediaAsset — video bytes or URI


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

## Configuration

> **Zero-config usage:** Call `VideoModule.configure()` with no arguments to use the `local-http` backend at `http://localhost:5004`.

### Option 1 — YAML file

```yaml
# application.yaml
multimedia:
  video:
    backend: "comfyui"
    comfyui_base_url: "http://localhost:8188"
    processing:
      max_concurrent_jobs: 4
```

### Option 2 — Profiles + Environment Variables

```bash
export LEX_PROFILE=production
export LEX_MULTIMEDIA__VIDEO__BACKEND=runway
export LEX_MULTIMEDIA__VIDEO__PROCESSING__MAX_CONCURRENT_JOBS=4
```

### Option 3 — Python

```python
from lexigram.multimedia.video import VideoModule
from lexigram.multimedia.video.config import VideoConfig, VideoProcessingConfig

VideoModule.configure(
    config=VideoConfig(
        backend="comfyui",
        processing=VideoProcessingConfig(max_concurrent_jobs=4),
    )
)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `backend` | `"local-http"` | `LEX_MULTIMEDIA__VIDEO__BACKEND` | `local-http`, `runway`, `openai`, `wan22`, `cogvideox`, `svd`, `comfyui` |
| `local_http_base_url` | `"http://localhost:5004"` | `LEX_MULTIMEDIA__VIDEO__LOCAL_HTTP_BASE_URL` | Local reference server URL |
| `runway_api_key_secret_name` | `"runway_api_key"` | `LEX_MULTIMEDIA__VIDEO__RUNWAY_API_KEY_SECRET_NAME` | Secret name for the Runway API key |
| `openai_api_key_secret_name` | `"openai_api_key"` | `LEX_MULTIMEDIA__VIDEO__OPENAI_API_KEY_SECRET_NAME` | Secret name for the OpenAI API key |
| `openai_model` | `"sora-2"` | `LEX_MULTIMEDIA__VIDEO__OPENAI_MODEL` | OpenAI video model |
| `openai_base_url` | `"https://api.openai.com"` | `LEX_MULTIMEDIA__VIDEO__OPENAI_BASE_URL` | OpenAI-compatible base URL |
| `wan22_base_url` | `"http://localhost:5200"` | `LEX_MULTIMEDIA__VIDEO__WAN22_BASE_URL` | Wan2.2 server URL |
| `cogvideox_base_url` | `"http://localhost:5201"` | `LEX_MULTIMEDIA__VIDEO__COGVIDEOX_BASE_URL` | CogVideoX server URL |
| `svd_base_url` | `"http://localhost:5202"` | `LEX_MULTIMEDIA__VIDEO__SVD_BASE_URL` | SVD server URL |
| `comfyui_base_url` | `"http://localhost:8188"` | `LEX_MULTIMEDIA__VIDEO__COMFYUI_BASE_URL` | ComfyUI server URL |
| `comfyui_checkpoint` | `"svd_xt_1_1.safetensors"` | `LEX_MULTIMEDIA__VIDEO__COMFYUI_CHECKPOINT` | ComfyUI checkpoint name |
| `comfyui_workflow_path` | `None` | `LEX_MULTIMEDIA__VIDEO__COMFYUI_WORKFLOW_PATH` | Path to a custom ComfyUI workflow JSON |
| `comfyui_fps` | `6` | `LEX_MULTIMEDIA__VIDEO__COMFYUI_FPS` | Output frames per second |
| `comfyui_motion_bucket_id` | `127` | `LEX_MULTIMEDIA__VIDEO__COMFYUI_MOTION_BUCKET_ID` | SVD motion bucket |
| `comfyui_poll_interval` | `1.0` | `LEX_MULTIMEDIA__VIDEO__COMFYUI_POLL_INTERVAL` | ComfyUI progress poll interval in seconds |
| `timeout` | `60.0` | `LEX_MULTIMEDIA__VIDEO__TIMEOUT` | Request timeout in seconds |
| `processing.ffmpeg_binary` | `"ffmpeg"` | `LEX_MULTIMEDIA__VIDEO__PROCESSING__FFMPEG_BINARY` | ffmpeg executable path |
| `processing.max_concurrent_jobs` | `2` | `LEX_MULTIMEDIA__VIDEO__PROCESSING__MAX_CONCURRENT_JOBS` | Max concurrent ffmpeg jobs |
| `processing.temp_dir` | `None` | `LEX_MULTIMEDIA__VIDEO__PROCESSING__TEMP_DIR` | Temp dir for intermediate frames |
| `processing.timeout` | `300.0` | `LEX_MULTIMEDIA__VIDEO__PROCESSING__TIMEOUT` | Processing job timeout in seconds |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `VideoModule.configure(config)` | Configure with explicit video config |
| `VideoModule.stub()` | Real module pinned to the default `local-http` backend for tests |

## Key Features

- **Seven generation backends** — `local-http`, `runway`, `openai`, `wan22`, `cogvideox`, `svd`, `comfyui`
- **`VideoProcessor`** — ffmpeg-backed editing: trim, concat, overlays, composition, subtitles, audio mux, thumbnails, GIF, transcode, speed, crop, color filters, raw filter graphs
- **Reference servers** — `lexigram-video-*-serve` console scripts run each local model server
- **Secret-managed API keys** — provider keys resolved by name through the secrets backend
- **Result-based** — `generate() -> Result[MediaAsset, MultimediaError]`; errors are domain values, not exceptions

## Testing

```python
from lexigram import Application
from lexigram.multimedia.video import VideoModule

async def test_boot():
    async with Application.boot(modules=[VideoModule.stub()]) as app:
        assert app.container is not None
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/multimedia/video/module.py` | `VideoModule.configure()` and `.stub()` |
| `src/lexigram/multimedia/video/config.py` | `VideoConfig`, `VideoProcessingConfig` |
| `src/lexigram/multimedia/video/di/provider.py` | `VideoGenerationProvider` — registers `VideoProvider` + `VideoProcessor`, wires task handlers |
| `src/lexigram/multimedia/video/providers/` | Generation backends (`local_http`, `runway`, `openai`, `wan22`, `cogvideox`, `svd`, `comfyui`) |
| `src/lexigram/multimedia/video/processing/` | ffmpeg-backed `VideoProcessor` (argv, ffmpeg, media I/O) |
| `src/lexigram/multimedia/video/servers/` | Reference-server entry points (`lexigram-video-*-serve`) |
| `src/lexigram/multimedia/video/tasks.py` | Background generation task handlers |
| `src/lexigram/multimedia/video/exceptions.py` | `VideoGenerationError` hierarchy |
