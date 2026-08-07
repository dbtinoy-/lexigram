"""Entry points for the realtime monitor demo.

Run::

    uv run python -m ops_console            # starts the web server on :7071
    uv run python -m ops_console --publish  # publish a sample event via HTTP
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import httpx

from lexigram.app import Application
from lexigram.web.server.runner import run_server_async
from ops_console.module import RealtimeModule


async def _serve(port: int) -> None:
    async with Application.boot(
        name="realtime-monitor",
        modules=[RealtimeModule.configure(port=port)],
    ) as app:
        from lexigram.web.di.provider import WebProvider

        web = await app.container.resolve(WebProvider)
        await run_server_async(web.starlette, host="127.0.0.1", port=port)


async def _publish(base_url: str, message: str) -> None:
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            f"{base_url}/api/events",
            json={"message": message, "severity": "info", "source": "cli"},
        )
        print(response.text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Realtime monitor demo")
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("REALTIME_PORT", "7071"))
    )
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

    if args.publish:
        asyncio.run(_publish(args.base_url, args.message))
    else:
        asyncio.run(_serve(args.port))
    return 0


if __name__ == "__main__":
    sys.exit(main())
