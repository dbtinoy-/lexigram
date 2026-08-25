"""Tests for the GenerationService pipeline (scripted fake runner)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from lexigram.builder.exceptions import GenerationError
from lexigram.builder.protocols import RunOutcome
from lexigram.builder.services.generation import GenerationService
from lexigram.builder.services.preview import PreviewService
from lexigram.builder.services.projects import ProjectService


class ScriptedRunner:
    """Returns queued outcomes in order; records every command."""

    def __init__(self, outcomes: list[RunOutcome]) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[tuple[str, ...]] = []

    async def run(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> RunOutcome:
        self.calls.append(tuple(command))
        if not self._outcomes:
            return RunOutcome(tuple(command), returncode=0)
        return self._outcomes.pop(0)


class FakeServer:
    def __init__(self) -> None:
        self.pid = 777
        self.terminated = False

    @property
    def alive(self) -> bool:
        return not self.terminated

    def terminate(self) -> None:
        self.terminated = True

    def is_running(self) -> bool:
        return not self.terminated


def build_stack(
    tmp_path: Path, outcomes: list[RunOutcome]
) -> tuple[GenerationService, ProjectService, PreviewService, ScriptedRunner, dict]:
    projects = ProjectService(tmp_path / "projects")
    spawner_state: dict = {"server": FakeServer(), "spawn_calls": 0}
    server: FakeServer = spawner_state["server"]

    class OneShotSpawner:
        async def start(self, command: list[str], *, cwd: Path) -> FakeServer:
            spawner_state["spawn_calls"] += 1
            spawner_state["last_cmd"] = list(command)
            return server

    previews = PreviewService(
        OneShotSpawner(),  # type: ignore[arg-type]
        health_check=lambda url: True,
        poll_interval=0.01,
    )
    runner = ScriptedRunner(outcomes)
    service = GenerationService(
        projects, previews, runner, port_probe=lambda port: True
    )
    return service, projects, previews, runner, spawner_state


SEED_DOC_NODES = """
from lexigram.builder.graph.models import (
    AppSettingsConfig,
    EntityConfig,
    FieldConfig,
    GraphDocument,
    GraphEdge,
    GraphNode,
    Position,
    RouteConfig,
)

doc = GraphDocument(
    version=1,
    nodes=(
        GraphNode("app_1", "app_settings", Position(0, 0),
                  AppSettingsConfig(app_name="notes_api", port=8110, db="sqlite")),
        GraphNode("ent_user", "entity", Position(1, 1),
                  EntityConfig(name="user",
                               fields=(FieldConfig(name="email", type="str"),))),
        GraphNode("rt_c", "route", Position(2, 2), RouteConfig(ops=("create", "list"))),
    ),
    edges=(GraphEdge("e1", "rt_c", "ent_user"),),
)
"""


async def test_happy_pipeline_order_and_live_summary(tmp_path: Path) -> None:
    exec(compile(SEED_DOC_NODES, "<seed>", "exec"), ns := {})
    doc = ns["doc"]

    service, projects, _previews, runner, state = build_stack(
        tmp_path, outcomes=[]
    )
    projects.create("notes_api")
    projects.save_graph("notes_api", doc)

    result = await service.generate("notes_api")

    assert result.is_ok()
    summary = result.unwrap()
    assert summary.project == "notes_api"
    assert summary.port == 8110
    assert summary.files_written >= 19

    commands = [c[:2] for c in runner.calls]
    assert ("uv", "sync") in commands
    assert ("uv", "run", "pytest") == commands[-1][:3] or (
        "uv",
        "run",
        "pytest",
        "-q",
    ) == tuple(runner.calls[-1])
    assert state["spawn_calls"] == 1
    generated_main = (
        tmp_path / "projects" / "notes_api" / "src" / "app" / "main.py"
    )
    assert generated_main.is_file()


async def test_test_failure_stops_preview_and_returns_err(tmp_path: Path) -> None:
    exec(compile(SEED_DOC_NODES, "<seed>", "exec"), ns := {})
    doc = ns["doc"]

    failing = RunOutcome(("uv", "run"), returncode=1, stderr="E       boom\n")
    service, projects, previews, _runner, state = build_stack(
        tmp_path, outcomes=[RunOutcome(("uv",), returncode=0), failing]
    )
    projects.create("notes_api")
    projects.save_graph("notes_api", doc)

    result = await service.generate("notes_api")

    assert result.is_err()
    err = result.unwrap_err()
    assert isinstance(err, GenerationError)
    assert "boom" in err.detail_tail
    # No boot ever happened; cleanup is a no-op stop.
    assert state["spawn_calls"] == 0
    assert previews.info("notes_api") is None


async def test_sync_failure_short_circuits(tmp_path: Path) -> None:
    exec(compile(SEED_DOC_NODES, "<seed>", "exec"), ns := {})
    doc = ns["doc"]

    sync_fail = RunOutcome(("uv", "sync"), returncode=7, stderr="lock error")
    service, projects, _previews, runner, _state = build_stack(
        tmp_path, outcomes=[sync_fail]
    )
    projects.create("notes_api")
    projects.save_graph("notes_api", doc)

    result = await service.generate("notes_api")

    assert result.is_err()
    assert "lock error" in result.unwrap_err().detail_tail
    # pytest never ran because syncing failed first.
    assert all("pytest" not in c for c in [tuple(x) for x in runner.calls]) or all(
        "pytest" not in " ".join(c) for c in runner.calls
    )


async def test_unknown_project_rejected_before_phases(tmp_path: Path) -> None:
    service, _projects, _previews, runner, _state = build_stack(tmp_path, [])

    result = await service.generate("ghost")

    assert result.is_err()
    assert runner.calls == []
