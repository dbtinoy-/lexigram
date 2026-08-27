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
    """Sync entry point: translate asyncio interrupts into exit codes."""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["main", "serve"]
