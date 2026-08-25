"""Serve the auth web demo.

Run::

    uv run python -m auth_web            # serves application.yaml (:8081)

Host/port come from ``application.yaml`` (``web.server``); override without
editing the file via ``LEX_WEB__SERVER__PORT``.
"""

from __future__ import annotations

import asyncio
import sys

from auth_web.app import create_app
from auth_web.config import load_lex_config
from lexigram.logging import get_logger

logger = get_logger(__name__)


async def serve() -> None:
    """Boot once and serve until interrupted; stop cleanly afterwards."""
    from lexigram.web.config import WebConfig
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server_async

    web_config = load_lex_config().get_section("web", WebConfig)
    app = create_app()
    try:
        await app.start()
        web = await app.container.resolve(WebProvider)
        logger.info(
            "server.listening", host=web_config.server.host, port=web_config.server.port
        )
        await run_server_async(
            web.starlette,
            host=web_config.server.host,
            port=web_config.server.port,
        )
    finally:
        await app.stop()


def main() -> int:
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
