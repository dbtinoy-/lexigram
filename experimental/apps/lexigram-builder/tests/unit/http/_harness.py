"""Shared boot harness for builder HTTP tests."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from lexigram.app.base import Application
from lexigram.builder.config import BuilderConfig
from lexigram.builder.controllers.builder_controller import BuilderController
from lexigram.builder.protocols import RunOutcome
from lexigram.builder.services.generation import GenerationService
from lexigram.builder.services.preview import PreviewService
from lexigram.builder.services.projects import ProjectService
from lexigram.web.config import RateLimitConfig, WebConfig
from lexigram.web.di.provider import WebProvider
from lexigram.web.security.config import CSRFConfig, SecurityConfig


def _test_web_config() -> WebConfig:
    return WebConfig(
        rate_limit=RateLimitConfig(enabled=False),
        security=SecurityConfig(csrf=CSRFConfig(enabled=False)),
    )


class ScriptedRunner:
    def __init__(self, outcomes: list[RunOutcome]) -> None:
        self._outcomes = list(outcomes)

    async def run(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> RunOutcome:
        if not self._outcomes:
            return RunOutcome(tuple(command), returncode=0)
        return self._outcomes.pop(0)


class FakeServer:
    pid = 31337

    def terminate(self) -> None:  # pragma: no cover - asserted via state only
        pass

    def is_running(self) -> bool:
        return True


class OneShotSpawner:
    def __init__(self) -> None:
        self.last_command: list[str] = []

    async def start(self, command: list[str], *, cwd: Path) -> FakeServer:
        self.last_command = list(command)
        return FakeServer()


class Harness:
    """Booted web app plus the fake-backed services behind it."""

    def __init__(
        self, client: Any, previews: PreviewService, projects: ProjectService
    ) -> None:
        self.client = client
        self.previews = previews
        self.projects = projects


def build_sync_client(
    tmp_path: Path, *, runner_outcomes: list[RunOutcome] | None = None
) -> Harness:
    from starlette.testclient import TestClient

    app = Application(name="builder-http-test")
    container = app.container

    projects = ProjectService(tmp_path / "projects")
    spawner = OneShotSpawner()
    previews = PreviewService(
        spawner,  # type: ignore[arg-type]
        health_check=lambda url: True,
        poll_interval=0.01,
    )
    generations = GenerationService(
        projects,
        previews,
        ScriptedRunner(runner_outcomes or []),
        port_probe=lambda port: True,
    )
    config = BuilderConfig()

    container.singleton(ProjectService, projects)
    container.singleton(PreviewService, previews)
    container.singleton(GenerationService, generations)
    container.singleton(BuilderConfig, config)

    web = WebProvider(
        controllers=[BuilderController],
        web_config=_test_web_config(),
    )
    loop = asyncio.new_event_loop()
    loop.run_until_complete(web.register(container))
    loop.run_until_complete(web.boot(container))
    harness = Harness(TestClient(web.starlette), previews, projects)
    harness.client._builder_loop = loop  # type: ignore[attr-defined]
    return harness


async def build_async_stack(
    tmp_path: Path, *, runner_outcomes: list[RunOutcome] | None = None
) -> tuple[Any, PreviewService]:
    import httpx

    app = Application(name="builder-http-async")
    container = app.container

    projects = ProjectService(tmp_path / "projects")
    previews = PreviewService(
        OneShotSpawner(),  # type: ignore[arg-type]
        health_check=lambda url: True,
        poll_interval=0.01,
    )
    generations = GenerationService(
        projects,
        previews,
        ScriptedRunner(runner_outcomes or []),
        port_probe=lambda port: True,
    )

    container.singleton(ProjectService, projects)
    container.singleton(PreviewService, previews)
    container.singleton(GenerationService, generations)
    container.singleton(BuilderConfig, BuilderConfig())

    web = WebProvider(
        controllers=[BuilderController],
        web_config=_test_web_config(),
    )
    await web.register(container)
    await web.boot(container)
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=web.starlette),
        base_url="http://test",
    )
    return client, previews
