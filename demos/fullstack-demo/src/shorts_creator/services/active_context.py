from __future__ import annotations

from dataclasses import dataclass

from shorts_creator.models.project import Project
from shorts_creator.models.run import Run
from shorts_creator.services.project_service import ProjectService
from shorts_creator.services.run_service import RunService


@dataclass(frozen=True)
class ActiveContext:
    run: Run
    project: Project


async def resolve_active_context(
    runs: RunService, projects: ProjectService
) -> ActiveContext | None:
    recent = await runs.list_recent(limit=1)
    if not recent:
        return None
    run = recent[0]
    project = await projects.get(run.project_id)
    if project is None:
        return None
    return ActiveContext(run=run, project=project)
