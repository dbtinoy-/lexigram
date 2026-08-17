"""Reference CogVideoX video generation server.

Run in a dedicated venv with the cogvideox-server extra installed:
  pip install lexigram-multimedia-video[cogvideox-server]
  lexigram-video-cogvideox-serve

NOTE: verify CogVideoXPipeline's constructor/inference signature against
the actually-installed diffusers/transformers version before relying on
this in production (design spec §11.1).
"""

from __future__ import annotations

from typing import Any

from aiohttp import web

MAX_BODY_BYTES: int = 64 * 1024 * 1024  # media payloads

_pipeline: Any = None


async def on_startup(app: web.Application) -> None:
    global _pipeline
    from diffusers import CogVideoXPipeline
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    _pipeline = CogVideoXPipeline.from_pretrained(
        "THUDM/CogVideoX-2b", torch_dtype=torch.float16
    ).to(device)


async def handle_generate(request: web.Request) -> web.Response:
    body = await request.json()
    video_bytes = _pipeline.generate(
        prompt=body["prompt"],
        duration_seconds=body.get("duration_seconds", 4.0),
        resolution=body.get("resolution", "1280x720"),
    )
    return web.Response(body=video_bytes, content_type="video/mp4")


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok" if _pipeline is not None else "loading"})


def main() -> None:
    app = web.Application(client_max_size=MAX_BODY_BYTES)
    app.on_startup.append(on_startup)
    app.router.add_post("/generate", handle_generate)
    app.router.add_get("/health", handle_health)
    web.run_app(app, port=5201)


if __name__ == "__main__":
    main()
