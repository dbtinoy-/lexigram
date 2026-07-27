"""Shared registry of live render tasks.

Controllers in lexigram are resolved per-request, so task bookkeeping that
must be visible across requests (cancel, duplicate detection, watchdogs)
cannot live on the controller. This singleton is injected instead.
"""

import asyncio


class RenderTaskRegistry:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}

    def register(self, run_id: str, task: asyncio.Task) -> None:
        self._tasks[run_id] = task

    def get(self, run_id: str) -> asyncio.Task | None:
        return self._tasks.get(run_id)

    def pop(self, run_id: str) -> asyncio.Task | None:
        return self._tasks.pop(run_id, None)
