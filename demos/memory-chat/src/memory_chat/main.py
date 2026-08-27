"""Entry point for the memory-chat demo.

Run::

    uv run python -m memory_chat

``create_app()`` builds the application.  This file boots it and
runs the web server.  Host/port are read automatically from
``application.yaml`` — no manual config wiring needed.

Lifecycle teaching notes:
- ``app.start()`` triggers the full lifecycle:
  register → freeze → boot (seeding happens here) → server start.
  The ``finally`` block ensures ``stop()`` runs even on errors.
- Inside the start/stop bracket the app is ``STARTED``: the container is
  frozen (no new registrations) yet fully resolvable — this is where
  servers run.  The three memory stores are ready too:
  ``ConciergeProvider.boot`` resolved them from ``MemoryModule`` and
  assembled the concierge during start.
- Resolving ``WebProvider`` here demonstrates post-start resolution; its
  auto-injected ``.config`` carries the server host/port.
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.logging import get_logger
from memory_chat.app import create_app

logger = get_logger(__name__)


async def serve() -> None:
    """Boot and serve until interrupted.

    ``app.start()`` triggers the full lifecycle:
    register → freeze → boot (seeding happens here) → server start.
    The ``finally`` block ensures ``stop()`` runs even on errors.
    """
    from lexigram.web.server.runner import run_server_async

    app = create_app()
    await app.start()
    try:
        # run_server_async reads host/port from application.yaml by default;
        # pass explicit kwargs to override (e.g. during tests).
        await run_server_async(app)
    finally:
        await app.stop()


def main() -> int:
    """Sync entry point: translate asyncio interrupts into exit codes.

    Convention: ``python -m <package>`` calls ``main()``.  Return 0 for
    success, 130 for keyboard interrupt — the shell will see this as the
    process exit code.
    """
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
