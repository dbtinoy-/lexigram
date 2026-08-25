"""Serve the support-agent demo.

Run::

    PYTHONPATH=demos/support-agent/src uv run python -m support_agent

Host/port come from ``application.yaml`` (``web.server``); override without
editing the file via ``LEX_WEB__SERVER__PORT``.
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.logging import get_logger
from support_agent.app import create_app
from support_agent.config import load_lex_config

logger = get_logger(__name__)


async def serve() -> None:
    """Boot once and serve until interrupted; stop cleanly afterwards."""
    from lexigram.web.config import WebConfig
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server_async

    config = load_lex_config()
    web_config = config.get_section("web", WebConfig)
    app = create_app(config)
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
