"""Reference HAT (Hybrid Attention Transformer) super-resolution server.

Run in a dedicated venv with torch + timm installed:
  pip install torch timm lexigram-multimedia-upscale
  lexigram-upscale-hat-serve

Loads the model once at process startup; never reloaded per-request.

NOTE: like real_esrgan_server.py, this is a new reference-server shape —
no equivalent file exists yet in any sibling package (see the plan-scope
note on the servers/ pattern).

NOTE: HAT has no single canonical PyPI package as of this writing — the
model weights/inference code are commonly vendored from the paper
authors' repo rather than installed via `timm` alone. Verify the actual
inference entrypoint against whatever HAT distribution is installed
before relying on this in production (design spec §11.1).
"""

from __future__ import annotations

import base64
from typing import Any

from aiohttp import web

MAX_BODY_BYTES: int = 64 * 1024 * 1024  # 25 MiB media x 4/3 base64 + JSON overhead

_model: Any = None


async def on_startup(app: web.Application) -> None:
    global _model
    from hat import HatSuperResolutionModel
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    _model = HatSuperResolutionModel(device=device)


async def handle_upscale(request: web.Request) -> web.Response:
    body = await request.json()
    image_bytes = base64.b64decode(body["image_bytes"])
    raw = body.get("scale_factor", 4)
    if not isinstance(raw, int) or raw not in (2, 4):
        raise web.HTTPBadRequest(text=f"scale_factor must be 2 or 4, got {raw!r}")
    scale_factor = raw
    upscaled_bytes = _model.upscale(image_bytes, scale_factor=scale_factor)
    return web.Response(body=upscaled_bytes, content_type="image/png")


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok" if _model is not None else "loading"})


def build_app() -> web.Application:
    """Build the reference server application with its explicit body cap."""

    app = web.Application(client_max_size=MAX_BODY_BYTES)
    app.on_startup.append(on_startup)
    app.router.add_post("/upscale", handle_upscale)
    app.router.add_get("/health", handle_health)
    return app


def main() -> None:
    web.run_app(build_app(), port=5401)


if __name__ == "__main__":
    main()
