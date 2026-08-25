"""Preview process ownership and SSE event fan-out."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from lexigram.builder.constants import PREVIEW_HEALTH_TIMEOUT_SECONDS
from lexigram.builder.exceptions import PreviewError
from lexigram.builder.protocols import ServerSpawner, SpawnedServer
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

_logger = get_logger(__name__)

HealthChecker = Callable[[str], "asyncio.Future[bool] | bool"]


@dataclass(frozen=True, slots=True)
class PreviewInfo:
    """Facts about a running preview server."""

    project: str
    pid: int
    port: int


class PreviewService:
    """Owns at most one running preview per project and broadcasts events.

    Events are plain dicts (``type`` = ``phase`` | ``log`` | ``diagnostic``
    | ``ping``). Subscribers receive an :class:`asyncio.Queue`; the
    service keeps a lazy heartbeat task pushing pings while any
    subscriber is attached.
    """

    def __init__(
        self,
        spawner: ServerSpawner,
        *,
        health_check: HealthChecker,
        health_timeout: float = PREVIEW_HEALTH_TIMEOUT_SECONDS,
        poll_interval: float = 0.25,
        heartbeat_interval: float = 15.0,
    ) -> None:
        self._spawner = spawner
        self._health_check = health_check
        self._health_timeout = health_timeout
        self._poll_interval = poll_interval
        self._heartbeat_interval = heartbeat_interval
        self._servers: dict[str, SpawnedServer] = {}
        self._ports: dict[str, int] = {}
        self._subscribers: list[asyncio.Queue[dict]] = []
        self._heartbeat_task: asyncio.Task[None] | None = None

    # ── lifecycle ────────────────────────────────────────────────────

    async def start(
        self, project: str, *, command: list[str], cwd: Path, port: int
    ) -> Result[PreviewInfo, PreviewError]:
        """Spawn the preview server and wait until /health responds."""
        if project in self._servers:
            await self.stop(project)
        try:
            server: SpawnedServer = await self._spawner.start(command, cwd=cwd)
        except Exception as exc:  # noqa: BLE001 - surfaced as domain error
            return Err(PreviewError(f"spawn failed: {exc}"))

        deadline = asyncio.get_running_loop().time() + self._health_timeout
        healthy = False
        while asyncio.get_running_loop().time() < deadline:
            if not server.is_running():
                break
            outcome = self._health_check(f"http://127.0.0.1:{port}/health")
            if bool(await _maybe_await(outcome)):
                healthy = True
                break
            await asyncio.sleep(self._poll_interval)

        if not healthy:
            server.terminate()
            return Err(PreviewError("preview did not become healthy before timeout"))

        self._servers[project] = server
        self._ports[project] = port
        self.publish({"type": "phase", "phase": "live", "port": port})
        _logger.info("preview_live", project=project, port=port, pid=server.pid)
        return Ok(PreviewInfo(project=project, pid=server.pid, port=port))

    async def stop(self, project: str) -> None:
        """Terminate the preview if running; safe to call repeatedly."""
        server = self._servers.pop(project, None)
        self._ports.pop(project, None)
        if server is None:
            return
        server.terminate()
        self.publish({"type": "phase", "phase": "stopped"})
        _logger.info("preview_stopped", project=project)

    def info(self, project: str) -> PreviewInfo | None:
        """Current running preview facts, or None."""
        server = self._servers.get(project)
        if server is None:
            return None
        return PreviewInfo(project=project, pid=server.pid, port=self._ports[project])

    def port_of(self, project: str) -> int | None:
        """Bound port for *project*, or None."""
        return self._ports.get(project)

    # ── event fan-out ────────────────────────────────────────────────

    def subscribe(self) -> asyncio.Queue[dict]:
        """Attach a queue receiving every published event."""
        queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=512)
        self._subscribers.append(queue)
        self._ensure_heartbeat()
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict]) -> None:
        """Detach a previously attached queue."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)
        if not self._subscribers and self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

    def publish(self, event: dict) -> None:
        """Fan out one event to every subscriber (drop-oldest per queue)."""
        for queue in list(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:  # pragma: no cover - raced
                    pass
            queue.put_nowait(event)

    def _ensure_heartbeat(self) -> None:
        if self._heartbeat_task is None or self._heartbeat_task.done():

            async def _beat() -> None:
                while True:
                    await asyncio.sleep(self._heartbeat_interval)
                    self.publish({"type": "ping"})

            self._heartbeat_task = asyncio.get_running_loop().create_task(_beat())


async def _maybe_await(value: object) -> bool:
    import inspect

    if inspect.isawaitable(value):
        return bool(await value)  # type: ignore[arg-type]
    return bool(value)


__all__ = ["HealthChecker", "PreviewInfo", "PreviewService"]
