"""Reference Real-ESRGAN super-resolution server.

Run in a dedicated venv with torch + realesrgan installed:
  pip install torch realesrgan lexigram-multimedia-upscale
  lexigram-upscale-real-esrgan-serve

Loads the model once at process startup; never reloaded per-request.

NOTE: this is the first checked-in reference-server implementation in
this codebase — no equivalent file exists yet in the TTS/music/video/image
sibling packages to copy from, so this shape is new, not a port of an
existing pattern (see the plan-scope note on the servers/ pattern).

NOTE: verify RealESRGANer's constructor/inference signature against the
actually-installed realesrgan package version before relying on this in
production (design spec §11.1).
"""

from __future__ import annotations

import base64
from typing import Any

from aiohttp import web

_model: Any = None


async def on_startup(app: web.Application) -> None:
    global _model
    import torch
    from realesrgan import RealESRGANer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    _model = RealESRGANer(device=device)


async def handle_upscale(request: web.Request) -> web.Response:
    body = await request.json()
    image_bytes = base64.b64decode(body["image_bytes"])
    scale_factor = body.get("scale_factor", 4)
    upscaled_bytes = _model.upscale(image_bytes, scale_factor=scale_factor)
    return web.Response(body=upscaled_bytes, content_type="image/png")


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok" if _model is not None else "loading"})


def main() -> None:
    app = web.Application()
    app.on_startup.append(on_startup)
    app.router.add_post("/upscale", handle_upscale)
    app.router.add_get("/health", handle_health)
    web.run_app(app, port=5400)


if __name__ == "__main__":
    main()
