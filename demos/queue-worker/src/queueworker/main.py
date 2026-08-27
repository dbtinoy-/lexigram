"""Serve the queue-worker REST API.

Convention followed: **Application boot** — ``create_app()`` builds the
composition root, this file boots it and runs the web server.  Host/port
are read automatically from ``application.yaml`` — no manual config wiring
needed.

Run::

    uv run python -m queueworker

The server exposes:

- ``POST /api/queue/publish``       — publish a message to the queue
- ``POST /api/queue/process``       — process a single message
- ``POST /api/queue/process/batch`` — process a batch of messages
- ``GET /api/queue/size``           — get queue size
- ``GET /api/queue/processed``      — get processed messages
- ``GET /api/queue/health``         — health check
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.logging import get_logger
from queueworker.app import create_app

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
