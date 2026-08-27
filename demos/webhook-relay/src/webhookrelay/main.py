"""Serve the webhook-relay REST API.

Convention followed: **Application boot** — ``create_app()`` builds the
composition root, this file boots it and runs the web server.  Host/port
are read automatically from ``application.yaml`` — no manual config wiring
needed.

Run::

    uv run python -m webhookrelay

The server exposes:

- ``POST /api/webhook/receive``      — receive and process a webhook
- ``POST /api/webhook/validate``     — validate a webhook signature
- ``GET /api/webhook/events``        — get all webhook events
- ``GET /api/webhook/events/count``  — get webhook event count
- ``GET /api/webhook/health``        — health check
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.logging import get_logger
from webhookrelay.app import create_app

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
