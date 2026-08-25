"""Serve the event-driven orders REST API.

Run::

    uv run python -m orders serve

Host/port come from ``application.yaml`` (``web.server``); override without
editing the file via ``LEX_WEB__SERVER__PORT``. Teaching commands
(place/pay/ship/list/outbox/demo) live in ``orders.cli``.
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.logging import get_logger
from orders.app import create_app
from orders.config import load_lex_config

logger = get_logger(__name__)


async def serve() -> None:
    """Boot once, wire buses eagerly, and serve until interrupted."""
    from lexigram.web.config import WebConfig
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server_async
    from orders.services.orders_api import OrdersApi

    config = load_lex_config()
    web_config = config.get_section("web", WebConfig)
    app = create_app(config)
    try:
        await app.start()
        await app.container.resolve(OrdersApi)  # eager bus/handler wiring
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
