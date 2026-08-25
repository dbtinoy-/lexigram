"""Single-port entry point: the hub embeds every demo under /demos/<slug>/.

Usage::

    PYTHONPATH=src uv run python -m demo_hub          # http://127.0.0.1:7000

Server host/port come from ``application.yaml`` (``web.server``); override
without editing the file via ``LEX_WEB__SERVER__PORT``. Each embedded demo
also runs standalone (see demos/README.md).
"""

from __future__ import annotations

import asyncio
import sys

from demo_hub.config import bind_web, load_lex_config
from demo_hub.module import DemoHubModule
from lexigram.app import Application
from lexigram.logging import get_logger

logger = get_logger(__name__)


async def _serve() -> None:
    from demo_hub.fleet import Fleet
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server_async

    web_config = bind_web()
    async with Application.boot(
        name="demo_hub",
        modules=[DemoHubModule.configure()],
        config=load_lex_config(),
    ) as app:
        web = await app.container.resolve(WebProvider)
        if web.starlette is None:
            raise RuntimeError("hub starlette app missing")
        fleet = await app.container.resolve(Fleet)
        await fleet.mount_all(web.starlette)
        await run_server_async(
            web.starlette,
            host=web_config.server.host,
            port=web_config.server.port,
        )
        # server returned — release embedded children
        await fleet.aclose()


def main() -> None:
    try:
        asyncio.run(_serve())
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
