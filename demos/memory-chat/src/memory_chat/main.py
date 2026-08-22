"""Entry points for the memory-chat demo.

Run::

    PYTHONPATH=demos/memory-chat/src uv run python -m memory_chat
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from lexigram.app import Application
from lexigram.web.server.runner import run_server_async
from memory_chat.module import MemoryChatModule


async def _serve(port: int) -> None:
    async with Application.boot(
        name="memory-chat",
        modules=[MemoryChatModule.configure(port=port)],
    ) as app:
        from lexigram.web.di.provider import WebProvider

        web = await app.container.resolve(WebProvider)
        await run_server_async(web.starlette, host="127.0.0.1", port=port)


def main() -> int:
    parser = argparse.ArgumentParser(description="Memory chat demo")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MEMORY_CHAT_PORT", "8083")),
    )
    args = parser.parse_args()
    asyncio.run(_serve(args.port))
    return 0


if __name__ == "__main__":
    sys.exit(main())
