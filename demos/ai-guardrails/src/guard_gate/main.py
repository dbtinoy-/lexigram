"""Entry points for the ai-guardrails demo.

Run::

    PYTHONPATH=demos/ai-guardrails/src uv run python -m guard_gate
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from lexigram.app import Application
from lexigram.web.server.runner import run_server_async

from guard_gate.module import GuardrailsModule


async def _serve(port: int) -> None:
    async with Application.boot(
        name="guard-gate",
        modules=[GuardrailsModule.configure(port=port)],
    ) as app:
        from lexigram.web.di.provider import WebProvider

        web = await app.container.resolve(WebProvider)
        await run_server_async(web.starlette, host="127.0.0.1", port=port)


def main() -> int:
    parser = argparse.ArgumentParser(description="AI guardrails demo")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("GUARD_GATE_PORT", "8084")),
    )
    args = parser.parse_args()
    asyncio.run(_serve(args.port))
    return 0


if __name__ == "__main__":
    sys.exit(main())
