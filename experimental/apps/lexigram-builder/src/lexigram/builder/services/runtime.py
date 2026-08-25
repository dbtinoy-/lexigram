"""Production adapters for the builder's process seams."""

from __future__ import annotations

import asyncio
from pathlib import Path
import subprocess  # noqa: S404 - controlled argv only

import httpx

from lexigram.builder.constants import PREVIEW_HEALTH_TIMEOUT_SECONDS
from lexigram.builder.protocols import RunOutcome, SpawnedServer

__all__ = [
    "AsyncSubprocessRunner",
    "UvicornSpawner",
    "default_projects_root",
    "httpx_health_check",
]


class AsyncSubprocessRunner:
    """Runs commands via ``asyncio.create_subprocess_exec``."""

    async def run(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> RunOutcome:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            return RunOutcome(
                command=tuple(command),
                returncode=-1,
                stderr="process timed out",
                timed_out=True,
            )
        return RunOutcome(
            command=tuple(command),
            returncode=process.returncode or 0,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
        )


class UvicornSpawner:
    """Starts detached uvicorn preview processes."""

    def __init__(self) -> None:
        self._handles: dict[int, subprocess.Popen[bytes]] = {}

    async def start(self, command: list[str], *, cwd: Path) -> SpawnedServer:
        process = await asyncio.to_thread(
            subprocess.Popen,  # noqa: S603 - fixed argv, no shell
            command,
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._handles[process.pid] = process
        return PopenServer(process)


class PopenServer:
    """SpawnedServer view over a Popen handle."""

    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self._process = process

    @property
    def pid(self) -> int:
        return self._process.pid

    def terminate(self) -> None:
        if self._process.poll() is None:
            self._process.terminate()

    def is_running(self) -> bool:
        return self._process.poll() is None


async def httpx_health_check(url: str) -> bool:
    """GET *url*/health style probe; True only on 2xx."""
    try:
        async with httpx.AsyncClient(
            timeout=PREVIEW_HEALTH_TIMEOUT_SECONDS / 6
        ) as client:
            response = await client.get(url)
            return response.is_success
    except httpx.HTTPError:
        return False


def default_projects_root() -> Path:
    """Package-local default: <lexigram-builder>/projects."""
    return Path(__file__).resolve().parents[4] / "projects"
