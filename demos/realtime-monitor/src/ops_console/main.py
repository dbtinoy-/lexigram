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
from lexigram.config.main import LexigramConfig
from lexigram.logging import get_logger
from lexigram.web.config import WebConfig
from lexigram.web.server.runner import run_server_async
from ops_console.config import APP_YAML
from ops_console.module import RealtimeModule

logger = get_logger(__name__)


async def _serve(config: LexigramConfig) -> None:
    from lexigram.web.di.provider import WebProvider

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Realtime monitor demo")
    parser.add_argument(
        "--publish", action="store_true", help="publish a sample event and exit"
    )
    parser.add_argument(
        "--message", default="Hello from CLI", help="message to publish"
    )
    parser.add_argument(
        "--base-url", default="http://127.0.0.1:7071", help="server base URL"
    )
    args = parser.parse_args()

    config = LexigramConfig.from_yaml(APP_YAML)
    if args.publish:
        asyncio.run(_publish(args.base_url, args.message))
    else:
        asyncio.run(_serve(config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
