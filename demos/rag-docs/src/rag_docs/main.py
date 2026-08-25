"""Serve the rag-docs REST API.

Run::

    uv run python -m rag_docs serve

Host/port come from ``application.yaml`` (``web.server``); override without
editing the file via ``LEX_WEB__SERVER__PORT``. Teaching commands
(index/ask/demo) live in ``rag_docs.cli``.
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.logging import get_logger
from rag_docs.app import create_app
from rag_docs.config import load_lex_config
from rag_docs.services.docs_ask import DocsAskService

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
        await app.container.resolve(DocsAskService)
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
