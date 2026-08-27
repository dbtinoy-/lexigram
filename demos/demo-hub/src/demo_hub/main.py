"""Entry point for the demo hub.

Run::

    PYTHONPATH=src uv run python -m demo_hub

``create_app()`` builds the application.  This file boots it,
mounts the child demos via Fleet, and runs the web server.
Host/port are read automatically from ``application.yaml`` —
no manual config wiring needed.
"""

from __future__ import annotations

import asyncio
import sys

from demo_hub.app import create_app
from lexigram.logging import get_logger

logger = get_logger(__name__)


async def serve() -> None:
    """Boot and serve until interrupted.

    ``app.start()`` triggers the full lifecycle:
    register → freeze → boot (Fleet mounts children here) → server start.
    The ``finally`` block ensures ``stop()`` runs even on errors.
    """
    from demo_hub.fleet import Fleet
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server

    app = create_app()
    await app.start()
    try:
        # Resolve the WebProvider to get the underlying Starlette app.
        web = await app.container.resolve(WebProvider)
        if web.starlette is None:
            raise RuntimeError("hub starlette app missing")

        # Mount every child demo under /demos/<slug>/.
        fleet = await app.container.resolve(Fleet)
        await fleet.mount_all(web.starlette)

        # run_server reads host/port from application.yaml by default;
        # pass explicit kwargs to override (e.g. during tests).
        run_server(app)

        # server returned — release embedded children
        await fleet.aclose()
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
