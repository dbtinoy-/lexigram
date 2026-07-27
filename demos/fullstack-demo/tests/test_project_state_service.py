import json

from shorts_creator.models.project import Project
from shorts_creator.models.run import Run, RunStatus
from shorts_creator.services.project_state import ProjectStateService


def make_project(id="p1", idea_json=None):
    return Project(id=id, topic="self_improvement", idea_json=idea_json)


def make_run(status=RunStatus.DRAFT, pid="p1", rid="r1"):
    return Run(id=rid, project_id=pid, status=status)


class _FakeProjectRepo:
    def __init__(self, projects):
        self._store = {p.id: p for p in projects}

    async def get(self, project_id):
        return self._store.get(project_id)


class _FakeRunRepo:
    def __init__(self, runs):
        self._store = {r.id: r for r in runs}

    async def list_by_project(self, project_id, limit=50):
        return [r for r in self._store.values() if r.project_id == project_id][:limit]

    async def list_recent(self, limit=50):
        return list(self._store.values())[:limit]


class TestForProject:
    async def test_returns_state_with_runs(self):
        project = make_project(idea_json=json.dumps([{"id": "a", "title": "T"}]))
        runs = [make_run(status=RunStatus.RENDERING)]
        svc = ProjectStateService(_FakeProjectRepo([project]), _FakeRunRepo(runs))
        state = await svc.for_project("p1")
        assert state is not None
        assert len(state.ideas) == 1
        assert state.active_run is not None
        assert state.stats["runs"] == 1

    async def test_returns_none_for_missing_project(self):
        svc = ProjectStateService(_FakeProjectRepo([]), _FakeRunRepo([]))
        assert await svc.for_project("nope") is None

    async def test_runs_none_is_tolerated(self):
        project = make_project(idea_json=json.dumps([{"id": "a"}]))
        svc = ProjectStateService(_FakeProjectRepo([project]), None)
        state = await svc.for_project("p1")
        assert state is not None
        assert state.stats["runs"] == 0


class TestForProjects:
    async def test_groups_runs_by_project(self):
        p1 = make_project(id="p1", idea_json=json.dumps([{"id": "a", "title": "T"}]))
        p2 = make_project(id="p2", idea_json=json.dumps([{"id": "b", "title": "U"}]))
        runs = [
            make_run(status=RunStatus.COMPLETED, pid="p1", rid="r1"),
            make_run(status=RunStatus.COMPLETED, pid="p2", rid="r2"),
        ]
        svc = ProjectStateService(_FakeProjectRepo([p1, p2]), _FakeRunRepo(runs))
        states = await svc.for_projects([p1, p2])
        assert states["p1"].stats["runs"] == 1
        assert states["p2"].stats["runs"] == 1

    async def test_empty_project_list(self):
        svc = ProjectStateService(_FakeProjectRepo([]), _FakeRunRepo([]))
        assert await svc.for_projects([]) == {}
