"""Tests for the project runs list page — the sidebar "All runs →" target.

Covers: route registration (via the controller's route table, the same
mechanism lexigram uses at app boot), uuid path-param acceptance, the
rendered run rows (newest first, same RunHistoryTable rows the history
page uses), and the standard 404 for unknown projects.
"""

from datetime import UTC, datetime

from starlette.routing import Match, Route

from shorts_creator.controllers.project_runs import ProjectRunsController
from shorts_creator.models.run import RunStatus

UUID = "123e4567-e89b-12d3-a456-426614174000"


class _FakeProject:
    def __init__(self, id, title="My Project"):
        self.id = id
        self.title = title


class _FakeRun:
    def __init__(
        self, id, title, status, created_at, project_id=UUID, duration_s=None, output_path=None
    ):
        self.id = id
        self.title = title
        self.status = status
        self.created_at = created_at
        self.project_id = project_id
        self.duration_s = duration_s
        self.output_path = output_path


class _FakeProjects:
    def __init__(self, projects=None):
        self.projects = projects or {}

    async def get(self, project_id):
        return self.projects.get(project_id)


class _FakeRuns:
    def __init__(self, runs=None):
        self.runs = runs or []
        self.last_project_id = None
        self.last_limit = None

    async def list_by_project(self, project_id, limit=50):
        self.last_project_id = project_id
        self.last_limit = limit
        return self.runs[:limit]


class _FakeLayout:
    def render(self, content="", title="", request=None):
        return f"<html><title>{title}</title>{content}</html>"


def _controller(project, runs):
    c = ProjectRunsController(
        projects=_FakeProjects({project.id: project}),
        runs=_FakeRuns(runs),
    )
    c.layout = _FakeLayout()
    return c


async def _body_of(resp) -> str:
    return resp.body if hasattr(resp, "body") else str(resp)


class TestRunsListRoute:
    def test_runs_list_route_is_registered(self):
        routes = {("GET", "/projects/{pid}/runs")}
        actual = {(r["method"], r["path"]) for r in ProjectRunsController.collect_routes()}
        assert routes <= actual

    def test_route_param_matches_the_sidebar_uuid_shape(self):
        route = Route("/projects/{pid}/runs", lambda scope: None)
        match, _ = route.matches(
            {
                "type": "http",
                "path": f"/projects/{UUID}/runs",
                "method": "GET",
                "query_string": b"",
                "headers": [],
            }
        )
        assert match is Match.FULL


class TestRunsListPage:
    def _dt(self, day):
        return datetime(2026, 1, day, 12, 0, tzinfo=UTC)

    async def test_renders_project_runs_rows(self):
        runs = [
            _FakeRun(
                "r2",
                "Newer Run",
                RunStatus.COMPLETED,
                self._dt(2),
                duration_s=12.5,
                output_path="data/renders/new.mp4",
            ),
            _FakeRun(
                "r1", "Older Run", RunStatus.FAILED, self._dt(1), output_path="data/renders/old.mp4"
            ),
        ]
        body = await _body_of(await _controller(_FakeProject(UUID), runs).run_list(pid=UUID))
        assert "Newer Run" in body
        assert "Older Run" in body
        assert "Completed" in body
        assert "Failed" in body
        assert "12.5s" in body
        assert "new.mp4" in body
        assert "2026-01-02 12:00" in body

    async def test_rows_newest_first(self):
        runs = [
            _FakeRun("r2", "Newer Run", RunStatus.COMPLETED, self._dt(2)),
            _FakeRun("r1", "Older Run", RunStatus.FAILED, self._dt(1)),
        ]
        body = await _body_of(await _controller(_FakeProject(UUID), runs).run_list(pid=UUID))
        assert body.index("Newer Run") < body.index("Older Run")

    async def test_queries_the_project_run_service(self):
        fake = _FakeRuns([])
        c = ProjectRunsController(projects=_FakeProjects({UUID: _FakeProject(UUID)}), runs=fake)
        c.layout = _FakeLayout()
        await c.run_list(pid=UUID)
        assert fake.last_project_id == UUID

    async def test_empty_project_shows_no_runs_state(self):
        body = await _body_of(await _controller(_FakeProject(UUID), []).run_list(pid=UUID))
        assert "No runs yet" in body

    async def test_unknown_project_returns_404(self):
        resp = await _controller(_FakeProject(UUID), []).run_list(
            pid="00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404
