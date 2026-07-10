"""Reference Stable Video Diffusion (SVD) server.

Run in a dedicated venv with the svd-server extra installed:
  pip install lexigram-multimedia-video[svd-server]
  lexigram-video-svd-serve

Requires image_uri in every request body — SVD has no text-to-video
path (design spec §6.3). The server itself resolves image_uri (HTTP GET
or local file read), never expects inlined bytes.

NOTE: verify StableVideoDiffusionPipeline's constructor/inference
signature against the actually-installed diffusers version before
relying on this in production (design spec §11.1).
"""

from __future__ import annotations

from typing import Any

from aiohttp import web

MAX_BODY_BYTES: int = 64 * 1024 * 1024  # media payloads

_pipeline: Any = None


async def on_startup(app: web.Application) -> None:
    global _pipeline
    from diffusers import StableVideoDiffusionPipeline  # type: ignore[import-not-found]
    import torch  # type: ignore[import-not-found]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    _pipeline = StableVideoDiffusionPipeline.from_pretrained(
        "stabilityai/stable-video-diffusion-img2vid-xt", torch_dtype=torch.float16
    ).to(device)


async def handle_generate(request: web.Request) -> web.Response:
    body = await request.json()
    video_bytes = _pipeline.generate(
        image_uri=body["image_uri"],
        resolution=body.get("resolution", "1024x576"),
    )
    return web.Response(body=video_bytes, content_type="video/mp4")


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok" if _pipeline is not None else "loading"})


def main() -> None:
    app = web.Application(client_max_size=MAX_BODY_BYTES)
    app.on_startup.append(on_startup)
    app.router.add_post("/generate", handle_generate)
    app.router.add_get("/health", handle_health)
    web.run_app(app, port=5202)


if __name__ == "__main__":
    main()
