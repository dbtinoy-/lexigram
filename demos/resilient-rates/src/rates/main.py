"""Standalone server entry point for the resilient-rates demo.

Run::

    cd demos/resilient-rates
    PYTHONPATH=src uv run python -m rates

Host/port come from ``application.yaml`` — no hardcoded values.
The rate desk's guided walkthrough is available from the browser console.
"""

from __future__ import annotations

import asyncio

from rates.app import create_app


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
    """Start the standalone rate desk server."""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main", "serve"]
