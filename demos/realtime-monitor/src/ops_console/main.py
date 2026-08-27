"""Entry point for the realtime monitor demo.

Run::

    uv run python -m ops_console
    uv run python -m ops_console --publish --message "deploy approved"

Host/port are read automatically from ``application.yaml`` — no manual
config wiring needed.  Override via env vars: ``LEX_WEB__SERVER__PORT=9000``.
"""

from __future__ import annotations

import argparse
import asyncio

import httpx

from lexigram.logging import get_logger
from ops_console.app import create_app

logger = get_logger(__name__)


async def serve() -> None:
    """Boot and serve until interrupted.

    ``app.start()`` triggers the full lifecycle:
    register → freeze → boot (heartbeat starts here) → server start.
    The ``finally`` block ensures ``stop()`` runs even on errors.
    """
    from lexigram.web.server.runner import run_server_async

    app = create_app()
    await app.start()
    try:
        await run_server_async(app)
    finally:
        await app.stop()


async def _publish(base_url: str, message: str) -> None:
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            f"{base_url}/api/events",
            json={"message": message, "severity": "info", "source": "cli"},
        )
    logger.info("publish.completed", status=response.status_code, body=response.text)


def _default_base_url() -> str:
    """Default target derived from this demo's own application.yaml."""
    from pathlib import Path

    from lexigram.config.main import LexigramConfig
    from lexigram.web.config import WebConfig

    yaml_path = Path(__file__).resolve().parents[2] / "application.yaml"
    web_config = LexigramConfig.from_yaml(yaml_path).get_section("web", WebConfig)
    return f"http://{web_config.server.host}:{web_config.server.port}"


def main() -> int:
    """Sync entry point: translate asyncio interrupts into exit codes."""
    parser = argparse.ArgumentParser(description="Realtime monitor demo")
    parser.add_argument(
        "--publish", action="store_true", help="publish a sample event and exit"
    )
    parser.add_argument(
        "--message", default="Hello from CLI", help="message to publish"
    )
    parser.add_argument(
        "--base-url",
        default=_default_base_url(),
        help="server base URL (default: from application.yaml)",
    )
    args = parser.parse_args()

    try:
        if args.publish:
            asyncio.run(_publish(args.base_url, args.message))
            return 0
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    main()
