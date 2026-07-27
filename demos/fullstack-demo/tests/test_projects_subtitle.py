from shorts_creator.controllers.projects import ProjectsController


class FakeProjectService:
    async def list_recent(self, limit=50):
        return []


class TestProjectsSubtitle:
    async def test_subtitle_matches_actual_table_columns(self):
        controller = ProjectsController(projects=FakeProjectService())
        html = await controller.list_projects(request=None)
        html_str = str(html)
        assert "status, and render output" not in html_str
        assert "AI video creation hubs" in html_str
