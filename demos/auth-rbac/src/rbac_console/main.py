"""Entry point for the auth-rbac console.

Run::

    uv run python -m rbac_console

``create_app()`` builds the application.  This file boots it and
runs the web server.  Host/port are read automatically from
``application.yaml`` — no manual config wiring needed.
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.logging import get_logger
from rbac_console.app import create_app

logger = get_logger(__name__)


async def serve() -> None:
    """Boot and serve until interrupted."""
    from lexigram.web.server.runner import run_server_async

    app = create_app()
    await app.start()
    try:
        # host/port auto-consumed from application.yaml by run_server_async
        # await run_server_async(app, host="0.0.0.0", port=9000)  # manual override
        await run_server_async(app)
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
