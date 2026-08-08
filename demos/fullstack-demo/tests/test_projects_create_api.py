import json

from shorts_creator.controllers.projects import ProjectsController
from shorts_creator.models.project import Project
from shorts_creator.services.project_service import ProjectService


class FakeProjectRepo:
    def __init__(self):
        self.store: dict[str, Project] = {}

    async def create(self, project):
        self.store[project.id] = project
        return project

    async def update(self, project):
        self.store[project.id] = project
        return project

    async def get(self, project_id):
        return self.store.get(project_id)


class FakeProjectService:
    def __init__(self, repo):
        self.repo = repo

    async def list_recent(self, limit=50):
        return list(self.repo.store.values())[:limit]

    async def create_project(self, *, title="", topic="self_improvement", focus="", overrides=None):
        overrides = overrides or {}
        project = Project(
            topic=topic,
            title=title,
            focus=focus,
            profile_overrides_json=json.dumps(overrides, separators=(",", ":")),
        )
        return await self.repo.create(project)


class FakeFormRequest:
    def __init__(self, form_data: dict[str, str]):
        self._form_data = form_data
        self.json_called = False

    async def form(self):
        return self._form_data

    async def json(self):
        self.json_called = True
        raise TypeError("no json body")


class TestCreateProjectAPI:
    def make_controller(self):
        return ProjectsController(projects=FakeProjectService(FakeProjectRepo()))

    async def test_create_persists_format_and_caption_style(self):
        controller = self.make_controller()
        await controller.upsert_project(
            request=FakeFormRequest(
                {
                    "title": "T",
                    "topic": "stoic",
                    "format": "topn",
                    "caption_style": "plain",
                    "focus": "f",
                }
            )
        )
        project = next(iter(controller.projects.repo.store.values()))
        assert project.format == "topn"
        assert project.caption_style == "plain"
        overrides = json.loads(project.profile_overrides_json)
        assert overrides["format_name"] == "topn"
        assert overrides["caption_style"] == "plain"

    async def test_create_skips_overrides_equal_to_inherited_default(self):
        controller = self.make_controller()
        await controller.upsert_project(
            request=FakeFormRequest(
                {
                    "title": "T",
                    "topic": "stoic",
                    "format": "narrated",
                    "caption_style": "plain",
                    "focus": "f",
                }
            )
        )
        project = next(iter(controller.projects.repo.store.values()))
        overrides = json.loads(project.profile_overrides_json)
        assert "format_name" not in overrides
        assert overrides["caption_style"] == "plain"

    async def test_create_defaults_format_and_caption_style(self):
        controller = self.make_controller()
        await controller.upsert_project(
            request=FakeFormRequest(
                {
                    "title": "T",
                    "topic": "stoic",
                }
            )
        )
        project = next(iter(controller.projects.repo.store.values()))
        assert project.format == "narrated"
        assert project.caption_style == "highlight"
        assert json.loads(project.profile_overrides_json) == {}

    async def test_create_without_request_uses_defaults(self):
        controller = self.make_controller()
        await controller.upsert_project(request=None)
        project = next(iter(controller.projects.repo.store.values()))
        assert project.format == "narrated"
        assert project.caption_style == "highlight"
        assert project.topic == "self_improvement"
        assert json.loads(project.profile_overrides_json) == {}

    async def test_create_persists_profile_overrides_json(self):
        controller = ProjectsController(projects=ProjectService(FakeProjectRepo()))
        await controller.upsert_project(
            request=FakeFormRequest(
                {
                    "title": "Morning Habits",
                    "topic": "self_improvement",
                    "format": "narrated",
                    "caption_style": "plain",
                    "duration_seconds": "45",
                }
            )
        )
        project = next(iter(controller.projects.repo.store.values()))
        overrides = json.loads(project.profile_overrides_json)
        assert overrides["duration_seconds"] == 45
        assert overrides["caption_style"] == "plain"
