"""Standalone server entry point for the realtime monitor demo.

Run::

    cd demos/realtime-monitor
    PYTHONPATH=src uv run python -m ops_console

Host/port are read automatically from ``application.yaml`` — no manual
config wiring needed. Override via env vars: ``LEX_WEB__SERVER__PORT=9000``.
Use the dashboard's Publish form to send events into the live stream.
"""

from __future__ import annotations

import asyncio

from ops_console.app import create_app


async def serve() -> None:
    """Boot and serve until interrupted.

    ``app.start()`` triggers the full lifecycle:
    register → freeze → boot (heartbeat starts here) → server start.
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
    """Start the standalone realtime dashboard server."""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
