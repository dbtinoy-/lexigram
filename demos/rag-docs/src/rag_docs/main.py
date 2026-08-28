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
from rag_docs.app import build_modules, build_providers, create_app

logger = get_logger(__name__)


async def run_cli_demo() -> None:
    """Run the three deterministic retrieval questions without a server."""
    from rag_docs.services import DocsAskService

    questions = (
        ("how do modules export services?", "vector"),
        ("what do providers register?", "mmr"),
        ("how does the outbox pattern work?", "vector"),
    )
    app = create_app()
    await app.start()
    try:
        service = await app.container.resolve(DocsAskService)
        for question, strategy in questions:
            result = await service.ask(question, strategy=strategy)
            if result.is_err():
                raise RuntimeError(str(result.unwrap_err()))
            answer = result.unwrap()
            logger.info(
                "demo.answer",
                question=question,
                strategy=strategy,
                answer=answer.answer,
                citations=list(answer.citations),
            )
        logger.info("demo.complete", questions=len(questions))
    finally:
        await app.stop()


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
    """Run the server, or the offline walkthrough when ``demo`` is passed."""
    try:
        if sys.argv[1:] == ["demo"]:
            asyncio.run(run_cli_demo())
        elif sys.argv[1:] in ([], ["serve"]):
            asyncio.run(serve())
        else:
            raise SystemExit(f"unknown command: {sys.argv[1]}")
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
