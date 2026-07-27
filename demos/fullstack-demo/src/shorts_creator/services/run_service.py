import json

from shorts_creator import RunNotFoundError
from shorts_creator.models.run import Run, RunStatus
from shorts_creator.services.render_progress import RenderProgressStore

_IMMUTABLE_SNAPSHOT_STATUSES = (RunStatus.RENDERING, RunStatus.COMPLETED)

_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.DRAFT: {RunStatus.RENDERING, RunStatus.FAILED},
    RunStatus.RENDERING: {RunStatus.COMPLETED, RunStatus.FAILED},
    RunStatus.FAILED: {RunStatus.RENDERING, RunStatus.FAILED},
}


class InvalidTransitionError(Exception):
    def __init__(self, current: RunStatus, target: RunStatus):
        super().__init__(f"Cannot transition run from {current} to {target}")
        self.current = current
        self.target = target


def _decode_snapshot(run: Run) -> dict:
    try:
        data = json.loads(run.settings_snapshot_json or "{}")
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


class RunService:
    def __init__(self, repo, render_progress: RenderProgressStore | None = None):
        self.repo = repo
        self.render_progress = render_progress or RenderProgressStore()

    def _transition(self, run: Run, target: RunStatus) -> None:
        allowed = _TRANSITIONS.get(run.status, set())
        if target not in allowed:
            raise InvalidTransitionError(run.status, target)
        run.status = target

    async def create(self, project_id: str, title: str = "") -> Run:
        run = Run(project_id=project_id, title=title)
        return await self.repo.create(run)

    async def create_with_profile(self, project_id: str, title: str, profile) -> Run:
        """Persist the resolved profile as the run's settings snapshot.

        The snapshot is written before any status transition, so a run's
        rendered settings can never disagree with what the pipeline used.
        """
        run = Run(
            project_id=project_id,
            title=title,
            settings_snapshot_json=json.dumps(profile.snapshot_dict(), separators=(",", ":")),
        )
        return await self.repo.create(run)

    async def get_snapshot(self, run_id: str) -> dict | None:
        """Return the run's decoded settings snapshot, or None."""
        run = await self.repo.get(run_id)
        if run is None or not run.settings_snapshot_json:
            return None
        return _decode_snapshot(run)

    async def update_profile_snapshot(self, run_id: str, values: dict) -> Run:
        """Merge `values` into the run's settings snapshot.

        The snapshot is immutable once the run starts rendering or finishes:
        rendering consumes the values, so a late edit would leave the pipeline
        and the DB row out of sync.
        """
        run = await self.repo.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        if run.status in _IMMUTABLE_SNAPSHOT_STATUSES:
            raise ValueError(
                f"run {run.id} settings snapshot is immutable after status {run.status.value}"
            )
        snapshot = _decode_snapshot(run)
        snapshot.update(values)
        run.settings_snapshot_json = json.dumps(snapshot, separators=(",", ":"))
        return await self.repo.update(run)

    async def link_idea(self, run_id: str, idea_id: str) -> Run:
        run = await self.repo.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        run.selected_idea_id = idea_id
        return await self.repo.update(run)

    async def get(self, run_id: str) -> Run | None:
        return await self.repo.get(run_id)

    async def resolve(self, run_id: str) -> Run:
        run = await self.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        return run

    async def list_by_project(self, project_id: str, limit: int = 50) -> list[Run]:
        return await self.repo.list_by_project(project_id, limit)

    async def list_status(self, status: RunStatus, limit: int = 10_000) -> list[Run]:
        """All runs in a status (not just the newest N), oldest first.

        Used by the startup sweep so stale "rendering" rows older than the
        newest page of runs are still failed instead of leaking forever.
        """
        return await self.repo.list_status(status.value, limit)

    async def mark_rendering(self, run_id: str) -> Run:
        run = await self.repo.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        self._transition(run, RunStatus.RENDERING)
        return await self.repo.update(run)

    async def mark_completed(self, run_id: str, output_path: str, duration_s: float) -> Run:
        run = await self.repo.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        self._transition(run, RunStatus.COMPLETED)
        run.output_path = output_path
        run.duration_s = duration_s
        return await self.repo.update(run)

    async def mark_failed(self, run_id: str, error: str) -> Run:
        run = await self.repo.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        self._transition(run, RunStatus.FAILED)
        run.error = error
        return await self.repo.update(run)

    async def update_stage_progress(self, run_id: str, stage: str, percent: int) -> Run:
        run = await self.repo.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        run.stage_progress = {**run.stage_progress, stage: percent}
        return await self.repo.update(run)

    async def on_stage(self, run_id: str, stage: str, progress: float, message: str) -> None:
        percent = int(progress * 100)
        await self.update_stage_progress(run_id, stage, percent)
        self.render_progress.push(
            run_id,
            {
                "event": "progress",
                "data": {"stage": stage, "progress": progress, "message": message},
            },
        )

    async def list_recent(self, limit: int = 50) -> list[Run]:
        return await self.repo.list_recent(limit)
