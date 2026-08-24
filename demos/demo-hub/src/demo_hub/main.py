"""Entry point for the demo-hub demo.

Usage::

    PYTHONPATH=src uv run python -m demo_hub
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
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server_async

    async with Application.boot(
        name="demo_hub", modules=[DemoHubModule.configure(port=port)]
    ) as app:
        web = await app.container.resolve(WebProvider)
        await run_server_async(web.starlette, host="127.0.0.1", port=port)


def main() -> None:
    port = int(os.environ.get("DEMO_HUB_PORT", "7000"))
    try:
        asyncio.run(_serve(port))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
