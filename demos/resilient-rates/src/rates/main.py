"""Serve the resilient-rates REST API.

Convention followed: **Application boot** — ``create_app()`` builds the
composition root, this file boots it and runs the web server.  Host/port
are read automatically from ``application.yaml`` — no manual config wiring
needed.

Run::

    uv run python -m rates

The server exposes:

- ``GET /``              — single-page rate desk console
- ``GET /rates/{pair}``  — quote via cache → single-flight → pipeline → stale
- ``GET /stats``         — hit/miss/upstream/retry/stale counters
- ``POST /scenario/{name}`` — flip upstream health live
- ``POST /cache/clear``  — drop cached quotes
- ``POST /stampede/{pair}`` — collapse N concurrent fetches into one call
- ``POST /demo``         — five-act guided walkthrough
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.logging import get_logger
from rates.app import create_app

logger = get_logger(__name__)


async def run_cli_demo() -> None:
    """Run the five-act walkthrough without starting an HTTP server."""
    from rates.controllers import RatesApiController

    app = create_app()
    await app.start()
    try:
        controller = await app.container.resolve(RatesApiController)
        if not await controller.run_demo():
            raise RuntimeError("the resilient-rates demo stopped before act 5")
        logger.info("demo.complete", acts=5)
    finally:
        await app.stop()


async def serve() -> None:
    """Boot and serve until interrupted.

    ``app.start()`` triggers the full lifecycle:
    register → freeze → boot (seeding happens here) → server start.
    The ``finally`` block ensures ``stop()`` runs even on errors.
    """
    from lexigram.web.server.runner import run_server

    app = create_app()
    await app.start()
    try:
        run_server(app)
    finally:
        await app.stop()


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


__all__ = ["main", "run_cli_demo", "serve"]
