from shorts_creator.controllers.projects import ProjectsController


class FakeProjectService:
    async def list_recent(self, limit=50):
        return []


class TestProjectsEmptyState:
    async def test_empty_state_has_no_dead_end_scripts_link(self):
        controller = ProjectsController(projects=FakeProjectService())
        html = await controller.list_projects(request=None)
        assert "/scripts" not in str(html)

    async def test_empty_state_uses_create_project_idea_video_copy(self):
        controller = ProjectsController(projects=FakeProjectService())
        html = await controller.list_projects(request=None)
        assert "Create Project" in str(html)
        assert "idea" in str(html)
        assert "video" in str(html)
