"""Generate pipeline: writing -> syncing -> testing -> booting -> live."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import socket

from lexigram.builder.constants import PREVIEW_PORT_RANGE_END, PREVIEW_PORT_RANGE_START
from lexigram.builder.exceptions import GenerationError
from lexigram.builder.gen.writer import ProjectWriter
from lexigram.builder.graph.models import AppSettingsConfig
from lexigram.builder.protocols import RunOutcome, SubprocessRunner
from lexigram.builder.services.preview import PreviewService
from lexigram.builder.services.projects import ProjectService
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

_logger = get_logger(__name__)

SYNC_TIMEOUT = 600.0
TEST_TIMEOUT = 900.0


@dataclass(frozen=True, slots=True)
class GenerationSummary:
    """Outcome of a successful pipeline run."""

    project: str
    files_written: int
    port: int
    pid: int

    @property
    def phases(self) -> tuple[str, ...]:
        """Canonical phase order for consumers asserting ordering."""
        return ("writing", "syncing", "testing", "booting", "live")


PortProbe = Callable[[int], bool]


def _default_port_probe(port: int) -> bool:
    """Return True when *port* can be bound on loopback (i.e. is free)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
        return True


class GenerationService:
    """Runs the five-phase generation pipeline for one project."""

    def __init__(
        self,
        projects: ProjectService,
        previews: PreviewService,
        runner: SubprocessRunner,
        *,
        writer: ProjectWriter | None = None,
        port_probe: PortProbe | None = None,
    ) -> None:
        self._projects = projects
        self._previews = previews
        self._runner = runner
        self._writer = writer or ProjectWriter(
            projects.projects_dir, post_process=False
        )
        self._port_probe = port_probe or _default_port_probe

    async def generate(
        self, name: str, *, requested_port: int | None = None
    ) -> Result[GenerationSummary, GenerationError]:
        """Validate, write, sync deps, test, and boot a live preview."""
        loaded = self._projects.load_validated(name)
        if loaded.is_err():
            err = loaded.unwrap_err()
            return Err(GenerationError(f"cannot generate {name!r}: {err.args[0]}"))

        self.publish_phase(name, "writing")
        await self._previews.stop(name)
        settings_config = loaded.unwrap().settings().config
        assert isinstance(settings_config, AppSettingsConfig)
        app_port = settings_config.port
        result = self._writer.write_project(loaded.unwrap())
        if not (result.files_created or result.files_overwritten):
            return Err(GenerationError("writer produced no files"))
        project_dir = self._projects.project_dir(name)

        self.publish_phase(name, "syncing")
        outcome = await self._run_step(name, ["uv", "sync"], project_dir, SYNC_TIMEOUT)
        if not isinstance(outcome, RunOutcome):
            return Err(outcome)

        self.publish_phase(name, "testing")
        outcome = await self._run_step(
            name, ["uv", "run", "pytest", "-q"], project_dir, TEST_TIMEOUT
        )
        if not isinstance(outcome, RunOutcome):
            return Err(outcome)

        self.publish_phase(name, "booting")
        port = self._select_port(requested_port or app_port)
        if port is None:
            return Err(GenerationError("no free preview port available"))
        boot = await self._previews.start(
            name,
            command=[
                "uv",
                "run",
                "uvicorn",
                "app.main:app",
                "--port",
                str(port),
            ],
            cwd=project_dir,
            port=port,
        )
        if boot.is_err():
            preview_err = boot.unwrap_err()
            return Err(GenerationError(f"preview boot failed: {preview_err}"))

        info = boot.unwrap()
        summary = GenerationSummary(
            project=name,
            files_written=len(result.files_created) + len(result.files_overwritten),
            port=info.port,
            pid=info.pid,
        )
        _logger.info("generation_complete", project=name, port=info.port)
        return Ok(summary)

    def publish_phase(self, name: str, phase: str) -> None:
        """Emit a phase event on the shared SSE bus."""
        self._previews.publish({"type": "phase", "project": name, "phase": phase})

    async def _run_step(
        self, name: str, command: list[str], cwd: Path, timeout: float
    ) -> RunOutcome | GenerationError:
        outcome = await self._runner.run(command, cwd=cwd, timeout=timeout)
        if not outcome.ok:
            await self._previews.stop(name)
            detail = outcome.tail()
            _logger.warning("pipeline_step_failed", project=name, command=command[0])
            return GenerationError(
                f"step {' '.join(command[:2])!r} failed (rc={outcome.returncode})",
                detail_tail=detail,
            )
        return outcome

    def _select_port(self, preferred: int) -> int | None:
        if self._port_probe(preferred):
            return preferred
        for candidate in range(PREVIEW_PORT_RANGE_START, PREVIEW_PORT_RANGE_END + 1):
            if self._port_probe(candidate):
                return candidate
        return None


__all__ = ["GenerationService", "GenerationSummary"]
