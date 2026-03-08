"""Reference Wan2.2 video generation server.

Run in a dedicated venv with the wan22-server extra installed:
  pip install lexigram-multimedia-video[wan22-server]
  lexigram-video-wan22-serve

Loads the model once at process startup; never reloaded per-request.
Supports both text-to-video and image-to-video (image_uri optional).

NOTE: Wan2.2 is under active development — verify its Python API's
constructor/inference signature against the actually-installed package
version before relying on this in production (design spec §11.1).
"""

from __future__ import annotations

from typing import Any

from aiohttp import web

_model: Any = None


async def on_startup(app: web.Application) -> None:
    global _model
    import torch  # type: ignore[import-not-found]
    from wan import WanT2V  # type: ignore[import-not-found]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    _model = WanT2V.from_pretrained(device=device)


async def handle_generate(request: web.Request) -> web.Response:
    body = await request.json()
    video_bytes = _model.generate(
        prompt=body["prompt"],
        duration_seconds=body.get("duration_seconds", 4.0),
        resolution=body.get("resolution", "1280x720"),
        image_uri=body.get("image_uri"),
    )
    return web.Response(body=video_bytes, content_type="video/mp4")


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok" if _model is not None else "loading"})


def main() -> None:
    app = web.Application()
    app.on_startup.append(on_startup)
    app.router.add_post("/generate", handle_generate)
    app.router.add_get("/health", handle_health)
    web.run_app(app, port=5200)


if __name__ == "__main__":
    main()
