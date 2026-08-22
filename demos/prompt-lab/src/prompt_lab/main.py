"""Entry points for the prompt-lab demo.

Run::

    PYTHONPATH=demos/prompt-lab/src uv run python -m prompt_lab
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from lexigram.app import Application
from lexigram.web.server.runner import run_server_async

from prompt_lab.module import PromptLabModule


async def _serve(port: int) -> None:
    async with Application.boot(
        name="prompt-lab",
        modules=[PromptLabModule.configure(port=port)],
    ) as app:
        from lexigram.web.di.provider import WebProvider

        web = await app.container.resolve(WebProvider)
        await run_server_async(web.starlette, host="127.0.0.1", port=port)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prompt lab demo")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PROMPT_LAB_PORT", "8085")),
    )
    args = parser.parse_args()
    asyncio.run(_serve(args.port))
    return 0


if __name__ == "__main__":
    sys.exit(main())
