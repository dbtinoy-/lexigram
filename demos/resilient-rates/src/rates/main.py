"""Serve the resilient-rates REST API.

Run::

    uv run python -m rates serve

Host/port come from ``application.yaml`` (``web.server``); override without
editing the file via ``LEX_WEB__SERVER__PORT``. The interactive walkthrough
lives in ``rates.cli`` (``uv run python -m rates demo``).
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.logging import get_logger
from rates.app import create_app
from rates.config import bind_web

logger = get_logger(__name__)


async def serve() -> None:
    """Boot once and serve until interrupted; stop cleanly afterwards."""
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server_async

    web_config = bind_web()
    app = create_app()
    try:
        await app.start()
        web = await app.container.resolve(WebProvider)
        logger.info(
            "server.listening",
            host=web_config.server.host,
            port=web_config.server.port,
        )
        await run_server_async(
            web.starlette,
            host=web_config.server.host,
            port=web_config.server.port,
        )
    finally:
        await app.stop()


def main() -> None:
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()


__all__ = ["main", "serve"]
