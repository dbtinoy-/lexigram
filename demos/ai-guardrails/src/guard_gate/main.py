"""Entry point for the ai-guardrails demo.

Run::

    uv run python -m guard_gate

Host/port come from ``application.yaml`` — no hardcoded values.

main.py is thin on purpose.  It only handles the async lifecycle
(start/stop) and signal translation (KeyboardInterrupt → exit code).
All composition lives in app.py.  For a real app, replace nothing here —
just swap which app you import.
"""

from __future__ import annotations

import asyncio
import sys

from guard_gate.app import create_app
from lexigram.logging import get_logger

logger = get_logger(__name__)


async def serve() -> None:
    """Boot and serve until interrupted.

    run_server_async reads host/port from application.yaml
    (web: section).  The try/finally ensures clean shutdown even on
    SIGINT.  In production, you'd add health checks and graceful
    drain here.
    """
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
