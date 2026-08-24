"""Single-port entry point: the hub embeds every demo under /demos/<slug>/.

Usage::

    PYTHONPATH=src uv run python -m demo_hub          # http://127.0.0.1:7000

Each demo also still runs standalone (see demos/README.md).
"""

from __future__ import annotations

import asyncio
import os
import sys

from demo_hub.module import DemoHubModule
from lexigram.app import Application
from lexigram.logging import get_logger

logger = get_logger(__name__)


async def _serve(port: int) -> None:
    from demo_hub.fleet import Fleet
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server_async

    async with Application.boot(
        name="demo_hub", modules=[DemoHubModule.configure(port=port)]
    ) as app:
        web = await app.container.resolve(WebProvider)
        if web.starlette is None:
            raise RuntimeError("hub starlette app missing")
        fleet = await app.container.resolve(Fleet)
        await fleet.mount_all(web.starlette)
        await run_server_async(web.starlette, host="127.0.0.1", port=port)
        # server returned — release embedded children
        await fleet.aclose()


def main() -> None:
    port = int(os.environ.get("DEMO_HUB_PORT", "7000"))
    try:
        asyncio.run(_serve(port))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
