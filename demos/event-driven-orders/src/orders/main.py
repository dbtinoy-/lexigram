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


async def run_cli_demo() -> None:
    """Run the full order lifecycle without starting an HTTP server."""
    from orders.controllers import OrdersApiController

    app = create_app()
    await app.start()
    try:
        controller = await app.container.resolve(OrdersApiController)
        result = await controller.run_demo()
        if result.is_err():
            raise RuntimeError(str(result.unwrap_err()))
        logger.info("demo.complete", result=result.unwrap())
    finally:
        await app.stop()


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
