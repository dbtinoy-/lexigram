"""Entry points for the realtime monitor demo.

Run::

    uv run python -m ops_console            # serves application.yaml (:7071)
    uv run python -m ops_console --publish  # publish a sample event via HTTP

Server host/port come from ``application.yaml`` (``web.server``); override
without editing the file via ``LEX_WEB__SERVER__PORT``.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import httpx

from lexigram.app import Application
from lexigram.logging import get_logger
from lexigram.web.config import WebConfig
from lexigram.web.server.runner import run_server_async
from ops_console.config import bind_application, load_lex_config
from ops_console.module import RealtimeModule

logger = get_logger(__name__)


async def _serve() -> None:
    from lexigram.web.di.provider import WebProvider

    config = load_lex_config()
    web_config = config.get_section("web", WebConfig)
    async with Application.boot(
        name="realtime-monitor",
        modules=[RealtimeModule.configure()],
        config=config,
    ) as app:
        web = await app.container.resolve(WebProvider)
        await run_server_async(
            web.starlette,
            host=web_config.server.host,
            port=web_config.server.port,
        )


async def _publish(base_url: str, message: str) -> None:
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            f"{base_url}/api/events",
            json={"message": message, "severity": "info", "source": "cli"},
        )
    logger.info("publish.completed", status=response.status_code, body=response.text)


def _default_base_url() -> str:
    """Default target derived from this demo's own application.yaml."""
    web_config, _demo_config = bind_application()
    return f"http://{web_config.server.host}:{web_config.server.port}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Realtime monitor demo")
    parser.add_argument(
        "--base-url",
        default=_default_base_url(),
        help="server base URL (default: from application.yaml)",
    )
    parser.add_argument(
        "--publish", action="store_true", help="publish a sample event and exit"
    )
    parser.add_argument(
        "--message", default="Hello from CLI", help="message to publish"
    )
    args = parser.parse_args()

    if args.publish:
        asyncio.run(_publish(args.base_url, args.message))
        return 0

    asyncio.run(_serve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
