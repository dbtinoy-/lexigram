"""Entry points for the support-agent demo.

Run::

    PYTHONPATH=demos/support-agent/src uv run python -m support_agent
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from lexigram.app import Application
from lexigram.web.server.runner import run_server_async

from support_agent.module import SupportAgentModule


async def _serve(port: int) -> None:
    async with Application.boot(
        name="support-agent",
        modules=[SupportAgentModule.configure(port=port)],
    ) as app:
        from lexigram.web.di.provider import WebProvider

        web = await app.container.resolve(WebProvider)
        await run_server_async(web.starlette, host="127.0.0.1", port=port)


def main() -> int:
    parser = argparse.ArgumentParser(description="Support agent demo")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("SUPPORT_AGENT_PORT", "8082")),
    )
    args = parser.parse_args()
    asyncio.run(_serve(args.port))
    return 0


if __name__ == "__main__":
    sys.exit(main())
