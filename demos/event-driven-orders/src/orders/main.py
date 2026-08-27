"""Entry point for the event-driven orders demo.

Run::

    cd demos/event-driven-orders
    PYTHONPATH=src uv run python -m orders

Host/port come from ``application.yaml`` — no hardcoded values.

Lifecycle teaching notes:
- ``Application.start()`` boots every provider in dependency order,
  freezes the container, and yields a fully-wired application.
- Resolving ``WebProvider`` after start demonstrates post-start
  resolution; its auto-injected ``.config`` carries the server host/port.
- The ``OrdersProvider.boot()`` resolves ``OrdersApi``, which triggers
  handler and event-subscription wiring exactly once (singleton factory).
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.logging import get_logger
from orders.app import create_app

logger = get_logger(__name__)


async def serve() -> None:
    """Boot once and serve until interrupted; stop cleanly afterwards."""
    from lexigram.web.server.runner import run_server

    app = create_app()
    await app.start()
    try:
        run_server(app)
    finally:
        await app.stop()


def main() -> int:
    """Sync wrapper: translate interrupts into a shell-friendly exit code."""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
