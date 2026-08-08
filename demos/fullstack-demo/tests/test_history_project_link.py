from typing import ClassVar

from starlette.responses import RedirectResponse

from shorts_creator.controllers.history import HistoryController
from shorts_creator.models.run import RunStatus


class FakeHistoryService:
    def __init__(self, run):
        self._run = run

    async def get_run(self, run_id):
        return self._run

    async def get_recent(self, limit=100):
        return [self._run] if self._run else []


class _MultiHistoryService:
    def __init__(self, runs):
        self._runs = {r["run_id"]: r for r in runs}

    async def get_run(self, run_id):
        return self._runs.get(run_id)

    async def get_recent(self, limit=100):
        return [v for v in self._runs.values()][:limit]


class _FakeDbRun:
    def __init__(
        self,
        id,
        project_id,
        status=RunStatus.DRAFT,
        output_path="",
        selected_idea_id=None,
        title="",
    ):
        self.id = id
        self.project_id = project_id
        self.status = status
        self.output_path = output_path
        self.selected_idea_id = selected_idea_id
        self.error = None
        self.title = title
        self.created_at = None
        self.duration_s = None


class FakeRunService:
    def __init__(self, run_by_id):
        self._run_by_id = run_by_id

    async def get(self, run_id):
        return self._run_by_id.get(run_id)

    async def list_recent(self, limit=100):
        return list(self._run_by_id.values())[:limit]


class _FakeProject:
    def __init__(self, id, title):
        self.id = id
        self.title = title


class FakeProjectService:
    def __init__(self, project):
        self._project = project

    async def get(self, project_id):
        return self._project if self._project and project_id == self._project.id else None

    async def list_recent(self, limit=50):
        return [self._project] if self._project else []


class FakeIdeaService:
    cached_ideas: ClassVar[list] = []


class TestHistoryRunDetailProjectLink:
    async def test_redirects_to_canonical_project_run_url_when_resolvable(self):
        run = {"run_id": "r1", "status": "completed", "idea": "Test Idea"}
        controller = HistoryController(
            history=FakeHistoryService(run),
            runs=FakeRunService({"r1": _FakeDbRun("r1", project_id="p1")}),
            projects=FakeProjectService(_FakeProject(id="p1", title="My Project")),
            ideas=FakeIdeaService(),
        )
        response = await controller.run_detail(request=None, run_id="r1")
        assert isinstance(response, RedirectResponse)
        assert response.status_code == 302
        assert response.headers.get("location") == "/projects/p1/runs/r1"

    async def test_renders_flat_detail_when_run_has_no_db_record(self):
        run = {"run_id": "orphan", "status": "completed", "idea": "Test Idea"}
        controller = HistoryController(
            history=FakeHistoryService(run),
            runs=FakeRunService({}),
            projects=FakeProjectService(_FakeProject(id="p1", title="My Project")),
            ideas=FakeIdeaService(),
        )
        html = await controller.run_detail(request=None, run_id="orphan")
        html_str = str(html)
        assert "/projects/p1/runs/orphan" not in html_str
        assert "Test Idea" in html_str


class TestHistoryMergedList:
    def _controller(self, snapshots, db_runs, project):
        return HistoryController(
            history=_MultiHistoryService(snapshots),
            runs=FakeRunService(db_runs),
            projects=FakeProjectService(project),
            ideas=FakeIdeaService(),
        )

    async def test_merges_db_runs_into_snapshot_list(self):
        snapshots = [
            {
                "run_id": "s1",
                "idea": "Snapshot Idea",
                "status": "completed",
                "created_at": "2026-08-01T10:00:00",
            }
        ]
        db_runs = {
            "s1": _FakeDbRun(
                "s1", "p1", status=RunStatus.COMPLETED, output_path="data/renders/a.mp4"
            ),
            "d1": _FakeDbRun("d1", "p1", status=RunStatus.DRAFT),
        }
        html = str(
            await self._controller(
                snapshots, db_runs, _FakeProject("p1", "My Project")
            ).list_history(request=None)
        )
        assert "2 of 2 total runs" in html
        assert "Snapshot Idea" in html
        assert "d1" in html

    async def test_db_only_drafts_are_counted_not_skipped(self):
        db_runs = {"d1": _FakeDbRun("d1", "p1", status=RunStatus.DRAFT)}
        html = str(
            await self._controller([], db_runs, _FakeProject("p1", "My Project")).list_history(
                request=None
            )
        )
        assert "1 of 1 total runs" in html
        assert "No pipeline runs recorded yet." not in html

    async def test_renders_empty_state_when_nothing_at_all(self):
        html = str(
            await self._controller([], {}, _FakeProject("p1", "My Project")).list_history(
                request=None
            )
        )
        assert "No pipeline runs recorded yet." in html

    async def test_project_column_shows_project_title(self):
        db_runs = {"d1": _FakeDbRun("d1", "p1", status=RunStatus.DRAFT)}
        html = str(
            await self._controller([], db_runs, _FakeProject("p1", "My Project")).list_history(
                request=None
            )
        )
        assert 'href="/projects/p1"' in html
        assert "My Project" in html
