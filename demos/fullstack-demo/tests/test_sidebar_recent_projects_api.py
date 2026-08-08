from shorts_creator.controllers.api.sidebar_api import SidebarApiController


class _FakeProject:
    def __init__(self, id, title):
        self.id = id
        self.title = title


class _FakeRun:
    def __init__(self, id, title):
        self.id = id
        self.title = title


class FakeProjectService:
    def __init__(self, projects):
        self._projects = projects
        self.last_limit = None

    async def list_recent(self, limit=5):
        self.last_limit = limit
        return self._projects[:limit]


class FakeRunService:
    def __init__(self, runs_by_project):
        self._runs_by_project = runs_by_project
        self.last_limit = None
        self.last_project_id = None

    async def list_by_project(self, project_id, limit=50):
        self.last_limit = limit
        self.last_project_id = project_id
        return self._runs_by_project.get(project_id, [])[:limit]


class _FakeRequest:
    def __init__(self, qp):
        self._qp = qp

    @property
    def query_params(self):
        return self._qp


class TestSidebarRecentProjects:
    async def test_lists_most_recent_projects(self):
        projects = [_FakeProject(id=f"p{i}", title=f"Morning Routine Reel {i}") for i in range(3)]
        controller = SidebarApiController(projects=FakeProjectService(projects))
        body = str(await controller.recent_projects())
        for p in projects:
            assert p.title in body
            assert f"/projects/{p.id}" in body
        assert "No projects yet" not in body

    async def test_requests_only_five_most_recent(self):
        service = FakeProjectService(
            [_FakeProject(id=f"p{i}", title=f"Project {i}") for i in range(7)]
        )
        controller = SidebarApiController(projects=service)
        body = str(await controller.recent_projects())
        assert service.last_limit == 5
        assert "Project 0" in body and "Project 4" in body
        assert "Project 5" not in body and "Project 6" not in body

    async def test_shows_empty_state_when_no_projects(self):
        controller = SidebarApiController(projects=FakeProjectService([]))
        body = str(await controller.recent_projects())
        assert "No projects yet" in body


class TestSidebarRecentRuns:
    async def test_lists_five_most_recent_runs_of_project(self):
        runs = [_FakeRun(id=f"r{i}", title=f"Morning Routine {i}") for i in range(3)]
        controller = SidebarApiController(
            projects=FakeProjectService([]),
            runs=FakeRunService({"p1": runs}),
        )
        body = str(await controller.recent_runs(request=_FakeRequest({"project_id": "p1"})))
        for r in runs:
            assert r.title in body
            assert f"/projects/p1/runs/{r.id}" in body
        assert "No runs yet" not in body

    async def test_requests_only_five_most_recent(self):
        runs = [_FakeRun(id=f"r{i}", title=f"Run {i}") for i in range(7)]
        service = FakeRunService({"p1": runs})
        controller = SidebarApiController(projects=FakeProjectService([]), runs=service)
        body = str(await controller.recent_runs(request=_FakeRequest({"project_id": "p1"})))
        assert service.last_limit == 5
        assert service.last_project_id == "p1"
        assert "Run 0" in body and "Run 4" in body
        assert "Run 5" not in body and "Run 6" not in body

    async def test_prompts_for_selection_when_no_project(self):
        controller = SidebarApiController(projects=FakeProjectService([]), runs=FakeRunService({}))
        body = str(await controller.recent_runs(request=_FakeRequest({})))
        assert "Select a project to see runs" in body

    async def test_shows_empty_state_when_project_has_no_runs(self):
        controller = SidebarApiController(projects=FakeProjectService([]), runs=FakeRunService({}))
        body = str(await controller.recent_runs(request=_FakeRequest({"project_id": "p1"})))
        assert "No runs yet" in body

    async def test_all_runs_footer_links_to_project_runs_page(self):
        runs = [_FakeRun(id="r1", title="Run 1")]
        controller = SidebarApiController(
            projects=FakeProjectService([]),
            runs=FakeRunService({"p1": runs}),
        )
        body = str(await controller.recent_runs(request=_FakeRequest({"project_id": "p1"})))
        assert "All runs" in body
        assert "/projects/p1/runs" in body

    async def test_no_footer_when_no_project_selected(self):
        controller = SidebarApiController(projects=FakeProjectService([]), runs=FakeRunService({}))
        body = str(await controller.recent_runs(request=_FakeRequest({})))
        assert "All runs" not in body
