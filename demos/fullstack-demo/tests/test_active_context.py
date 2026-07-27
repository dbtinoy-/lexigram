from dataclasses import dataclass

from shorts_creator.services.active_context import resolve_active_context


@dataclass
class _FakeRun:
    id: str
    project_id: str


@dataclass
class _FakeProject:
    id: str
    title: str


class FakeRunService:
    def __init__(self, recent):
        self._recent = recent

    async def list_recent(self, limit=1):
        return self._recent[:limit]


class FakeProjectService:
    def __init__(self, project_by_id):
        self._project_by_id = project_by_id

    async def get(self, project_id):
        return self._project_by_id.get(project_id)


class TestResolveActiveContext:
    async def test_returns_most_recent_run_with_its_project(self):
        run = _FakeRun(id="r1", project_id="p1")
        project = _FakeProject(id="p1", title="Morning Routine Reel")
        ctx = await resolve_active_context(
            runs=FakeRunService([run]),
            projects=FakeProjectService({"p1": project}),
        )
        assert ctx is not None
        assert ctx.run is run
        assert ctx.project is project

    async def test_returns_none_when_no_runs_exist(self):
        ctx = await resolve_active_context(
            runs=FakeRunService([]),
            projects=FakeProjectService({}),
        )
        assert ctx is None

    async def test_returns_none_when_run_points_to_missing_project(self):
        run = _FakeRun(id="r1", project_id="ghost")
        ctx = await resolve_active_context(
            runs=FakeRunService([run]),
            projects=FakeProjectService({}),
        )
        assert ctx is None
