"""Entry point for the feedback-loop demo.

Run::

    uv run python -m feedback_loop

``create_app()`` builds the application.  This file boots it and
runs the web server.  Host/port are read automatically from
``application.yaml`` — no manual config wiring needed.

Convention: thin entry point.  Composition lives in ``app.py``;
lifecycle (start/stop) is delegated to the framework runner.
"""

from __future__ import annotations

import asyncio
import sys

from feedback_loop.app import create_app
from lexigram.logging import get_logger

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
    """Sync entry point: translate asyncio interrupts into exit codes."""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
