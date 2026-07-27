"""Canonical per-project pipeline state.

Every page (projects list, dashboard, scripts, render, history, run
panels) derives its view from ProjectState so the whole app agrees on
where a project is in the pipeline. This module is the single place
that knows how to compute that state from a project row + its runs.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from shorts_creator.models.run import Run, RunStatus

STAGE_KEYS = ("ideas", "script", "render")


def parse_idea_json(raw: str | None) -> list[dict]:
    """Parse project.idea_json into a list of idea dicts. Never raises."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return data if isinstance(data, list) else [data]


def _first_script(ideas: list[dict]) -> dict | None:
    for idea in ideas:
        sj = idea.get("script_json")
        if not sj:
            continue
        try:
            return json.loads(sj)
        except (json.JSONDecodeError, TypeError):
            continue
    return None


@dataclass
class ProjectState:
    project_id: str
    ideas: list[dict] = field(default_factory=list)
    script_indices: set[int] = field(default_factory=set)
    rendered_indices: set[int] = field(default_factory=set)
    active_run: Run | None = None
    latest_run: Run | None = None
    recent_runs: list[Run] = field(default_factory=list)
    stage: str = "ideas"
    stats: dict[str, int] = field(default_factory=dict)
    stage_state: list[dict] = field(default_factory=list)


def derive_project_state(project, runs: list[Run], file_exists=os.path.exists) -> ProjectState:
    """Derive the full pipeline state for one project from its row + runs."""
    pid = getattr(project, "id", "")
    ideas = parse_idea_json(getattr(project, "idea_json", None))
    script_indices = {
        i
        for i, d in enumerate(ideas)
        if isinstance(d.get("script_json"), str) and d["script_json"].strip()
    }
    completed_idea_ids = {
        r.selected_idea_id
        for r in runs
        if r.status == RunStatus.COMPLETED
        and r.output_path
        and r.selected_idea_id
        and file_exists(r.output_path)
    }
    rendered_indices = {i for i, d in enumerate(ideas) if d.get("id") in completed_idea_ids}
    active_run = next((r for r in runs if r.status == RunStatus.RENDERING), None) or next(
        (r for r in runs if r.status == RunStatus.QUEUED), None
    )
    latest_run = runs[0] if runs else None

    if not ideas:
        stage = "ideas"
    elif not script_indices:
        stage = "script"
    elif not rendered_indices:
        stage = "render"
    else:
        stage = "done"

    first_idea = ideas[0] if ideas else None
    script = _first_script(ideas)
    completed_runs = [r for r in runs if r.status == RunStatus.COMPLETED and r.output_path]

    stage_state = [
        {
            "key": "ideas",
            "done": bool(ideas),
            "active": stage == "ideas",
            "preview": f"{len(ideas)} idea{'s' if len(ideas) != 1 else ''}" if ideas else "",
            "summary": (first_idea.get("title", "") or "")[:55] if first_idea else "",
        },
        {
            "key": "script",
            "done": bool(script_indices),
            "active": stage == "script",
            "preview": f"{script.get('total_duration', 0):.0f}s · {script.get('word_count', 0)} words"
            if script
            else "",
            "summary": (script.get("title", "") or "")[:55] if script else "",
        },
        {
            "key": "render",
            "done": bool(rendered_indices),
            "active": stage == "render",
            "preview": f"{completed_runs[0].duration_s:.1f}s video"
            if completed_runs and completed_runs[0].duration_s
            else "",
            "summary": os.path.basename(completed_runs[0].output_path or "")
            if completed_runs
            else "",
        },
    ]

    return ProjectState(
        project_id=pid,
        ideas=ideas,
        script_indices=script_indices,
        rendered_indices=rendered_indices,
        active_run=active_run,
        latest_run=latest_run,
        recent_runs=list(runs),
        stage=stage,
        stats={
            "ideas": len(ideas),
            "scripts": len(script_indices),
            "videos": len(rendered_indices),
            "runs": len(runs),
        },
        stage_state=stage_state,
    )


class ProjectStateService:
    """Loads projects + runs and returns canonical ProjectState objects.

    ``runs`` may be None (unit tests / controllers without a RunService);
    run lookups are then skipped and all run-derived fields stay empty.
    """

    def __init__(self, projects, runs):
        self.projects = projects
        self.runs = runs

    async def for_project(self, project_id: str) -> ProjectState | None:
        project = await self.projects.get(project_id)
        if project is None:
            return None
        return derive_project_state(project, await self._runs_for(project_id))

    async def for_projects(self, projects) -> dict[str, ProjectState]:
        runs_by_project: dict[str, list[Run]] = {}
        if self.runs is not None:
            try:
                for r in await self.runs.list_recent(limit=200):
                    runs_by_project.setdefault(r.project_id, []).append(r)
            except Exception:  # noqa: BLE001, S110 - tolerance: DB hiccup must not break the projects page
                pass
        return {p.id: derive_project_state(p, runs_by_project.get(p.id, [])) for p in projects}

    async def _runs_for(self, project_id: str) -> list[Run]:
        if self.runs is None:
            return []
        try:
            return await self.runs.list_by_project(project_id, limit=50)
        except Exception:  # noqa: BLE001 - tolerance: run lookup failure degrades to no-runs state
            return []
