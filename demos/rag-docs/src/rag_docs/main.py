"""Entry point for the rag-docs REST API.

Run::

    uv run python -m rag_docs

Host/port come from ``application.yaml`` (``web.server``); override without
editing the file via ``LEX_WEB__SERVER__PORT``.

Lifecycle teaching notes:
- ``Application.boot(...)`` is the idiomatic context manager: it creates the
  app, starts every provider in dependency order, yields, and *guarantees*
  ``stop()`` runs on exit — even on exceptions or Ctrl-C.
- Inside the block the app is ``STARTED``: the container is frozen (no new
  registrations) yet fully resolvable — this is where servers run.  The RAG
  index is ready too: ``DocsAskProvider.boot`` ingested and embedded the
  corpus during start, before the first question arrives.
- Resolving ``WebProvider`` here demonstrates post-start resolution; its
  auto-injected ``.config`` carries the server host/port.
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.logging import get_logger
from rag_docs.app import build_modules, build_providers

logger = get_logger(__name__)


async def serve() -> None:
    """Boot once and serve until interrupted; stop cleanly afterwards."""
    from lexigram.app.base import Application
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server

    async with Application.boot(
        name="rag-docs",
        modules=build_modules(),
        providers=build_providers(),
    ) as app:
        web = await app.container.resolve(WebProvider)
        server = web.config.server
        logger.info("server.listening", host=server.host, port=server.port)
        run_server(web.starlette, host=server.host, port=server.port)


def main() -> int:
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
