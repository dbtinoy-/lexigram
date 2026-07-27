from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator

KEEP_ALIVE_INTERVAL = 15.0


class RenderProgressStore:
    def __init__(self, keep_alive: float = KEEP_ALIVE_INTERVAL) -> None:
        self._queues: dict[str, asyncio.Queue] = {}
        self._last_activity: dict[str, float] = {}
        self._stage_started: dict[str, tuple[str, float]] = {}
        self._keep_alive = keep_alive

    def create_queue(self, run_id: str) -> None:
        if run_id not in self._queues:
            self._queues[run_id] = asyncio.Queue()
            self._last_activity[run_id] = time.monotonic()

    def push(self, run_id: str, event: dict) -> None:
        queue = self._queues.get(run_id)
        if queue is not None:
            queue.put_nowait(event)
            self._last_activity[run_id] = time.monotonic()
            stage = (event.get("data") or {}).get("stage")
            if stage and event.get("event") == "progress":
                current, _ = self._stage_started.get(run_id, ("", 0.0))
                if current != stage:
                    self._stage_started[run_id] = (stage, time.monotonic())

    def last_activity(self, run_id: str) -> float | None:
        return self._last_activity.get(run_id)

    def stage_elapsed(self, run_id: str) -> float | None:
        started = self._stage_started.get(run_id)
        if started is None:
            return None
        _, t0 = started
        return time.monotonic() - t0

    async def subscribe(self, run_id: str) -> AsyncGenerator[dict | str, None]:
        queue = self._queues.get(run_id)
        if queue is None:
            return
        yield {"event": "connected", "data": {"status": "waiting"}}
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=self._keep_alive)
                yield event
                if event.get("event") in ("complete", "failed", "cancelled"):
                    break
            except TimeoutError:
                yield ": keep-alive\n\n"
        self._queues.pop(run_id, None)
        self._last_activity.pop(run_id, None)
        self._stage_started.pop(run_id, None)
