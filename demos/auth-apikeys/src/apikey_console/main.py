"""Serve the API-keys console.

Run::

    uv run python -m apikey_console            # serves application.yaml (:8091)

Host/port come from ``application.yaml`` (``web.server``); override without
editing the file via ``LEX_WEB__SERVER__PORT``.
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.logging import get_logger

logger = get_logger(__name__)


async def serve() -> None:
    """Boot once and serve until interrupted; stop cleanly afterwards."""
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server_async

    app = create_app()
    try:
        await app.start()
        web = await app.container.resolve(WebProvider)
        server = web.web_config.server  # resolved from application.yaml
        logger.info("server.listening", host=server.host, port=server.port)
        await run_server_async(web.starlette, host=server.host, port=server.port)
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
