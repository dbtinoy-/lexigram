"""Reference RIFE frame-interpolation server.

Run in a dedicated venv with the rife-server extra installed:
  pip install lexigram-multimedia-interpolate[rife-server]
  lexigram-interpolate-rife-serve

Loads the model once at process startup; never reloaded per-request.

NOTE: RIFE has no single stable official PyPI package as of this
writing — most real deployments vendor a specific reference
implementation directly rather than pip-installing a maintained
package. Verify the actual install/import mechanism against whatever
RIFE distribution is used before relying on this in production
(design spec §11.1).
"""

from __future__ import annotations

import base64
from typing import Any

from aiohttp import web

MAX_BODY_BYTES: int = 64 * 1024 * 1024  # media payloads, base64 window

_model: Any = None


async def on_startup(app: web.Application) -> None:
    global _model
    from rife import RifeModel  # type: ignore[import-not-found]
    import torch  # type: ignore[import-not-found]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    _model = RifeModel(device=device)


async def handle_interpolate(request: web.Request) -> web.Response:
    body = await request.json()
    frame_a_bytes = base64.b64decode(body["frame_a_bytes"])
    frame_b_bytes = base64.b64decode(body["frame_b_bytes"])
    midpoint_bytes = _model.interpolate(frame_a_bytes, frame_b_bytes)
    return web.Response(body=midpoint_bytes, content_type="image/png")


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok" if _model is not None else "loading"})


def main() -> None:
    app = web.Application(client_max_size=MAX_BODY_BYTES)
    app.on_startup.append(on_startup)
    app.router.add_post("/interpolate", handle_interpolate)
    app.router.add_get("/health", handle_health)
    web.run_app(app, port=5500)


if __name__ == "__main__":
    main()
