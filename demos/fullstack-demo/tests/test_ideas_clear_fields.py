"""Blank idea fields must clear the stored value (presence-based updates)."""

import pytest

from shorts_creator.controllers.api.ideas_api import IdeasApiController
from shorts_creator.services.core import AppConfig
from shorts_creator.services.progress_store import ProgressStore


class _FakeProject:
    def __init__(self, idea_json):
        self.idea_json = idea_json


class _FakeProjects:
    def __init__(self, idea_json=None):
        self._idea_json = idea_json
        self.updated = []

    async def get(self, project_id):
        if self._idea_json is None:
            return None
        return _FakeProject(self._idea_json)

    async def update_idea(self, project_id, idea_id, updates):
        self.updated.append((project_id, idea_id, updates))


class _FakeIdeas:
    async def generate_ideas(self, **kwargs):
        return []


class _FakeTaskManager:
    def __init__(self) -> None:
        self.tasks: list[tuple[str, object]] = []

    def track_named(self, name, coro):
        self.tasks.append((name, coro))

    def close_tasks(self):
        pass


class _FakeRequest:
    def __init__(self, body=None, headers=None):
        self.headers = headers or {"content-type": "application/json"}
        self._body = body or {}

    async def json(self):
        return self._body


def _make_controller(projects):
    return IdeasApiController(
        ideas=_FakeIdeas(),
        config=AppConfig(),
        projects=projects,
        progress_store=ProgressStore(),
        task_manager=_FakeTaskManager(),
    )


@pytest.fixture
def idea_project():
    return _FakeProjects(
        idea_json='[{"id": "i1", "title": "T", "hook_line": "Old hook", '
        '"core_message": "Old core", "target_audience": "Old audience"}]'
    )


def _updates(controller):
    return controller.projects.updated[-1][2] if controller.projects.updated else {}


class TestIdeaClearOnBlank:
    async def test_blank_hook_line_clears_stored_value(self, idea_project):
        controller = _make_controller(idea_project)
        await controller.update(
            request=_FakeRequest(
                {
                    "project_id": "proj-1",
                    "idea_index": 0,
                    "title": "T",
                    "hook_line": "",
                    "core_message": "Old core",
                    "target_audience": "Old audience",
                }
            )
        )
        assert _updates(controller)["hook_line"] == ""

    async def test_blank_core_message_clears_stored_value(self, idea_project):
        controller = _make_controller(idea_project)
        await controller.update(
            request=_FakeRequest(
                {
                    "project_id": "proj-1",
                    "idea_index": 0,
                    "title": "T",
                    "hook_line": "Old hook",
                    "core_message": "",
                    "target_audience": "Old audience",
                }
            )
        )
        assert _updates(controller)["core_message"] == ""

    async def test_missing_key_in_json_keeps_value(self, idea_project):
        controller = _make_controller(idea_project)
        await controller.update(
            request=_FakeRequest(
                {
                    "project_id": "proj-1",
                    "idea_index": 0,
                    "title": "Renamed",
                }
            )
        )
        updates = _updates(controller)
        assert "hook_line" not in updates
        assert updates["title"] == "Renamed"

    async def test_blank_target_audience_clears(self, idea_project):
        controller = _make_controller(idea_project)
        await controller.update(
            request=_FakeRequest(
                {
                    "project_id": "proj-1",
                    "idea_index": 0,
                    "title": "T",
                    "hook_line": "Old hook",
                    "core_message": "Old core",
                    "target_audience": "",
                }
            )
        )
        assert _updates(controller)["target_audience"] == ""

    async def test_nonblank_values_still_update(self, idea_project):
        controller = _make_controller(idea_project)
        await controller.update(
            request=_FakeRequest(
                {
                    "project_id": "proj-1",
                    "idea_index": 0,
                    "title": "T",
                    "hook_line": "New hook",
                    "core_message": "New core",
                    "target_audience": "New audience",
                }
            )
        )
        updates = _updates(controller)
        assert updates["hook_line"] == "New hook"
        assert updates["core_message"] == "New core"
        assert updates["target_audience"] == "New audience"


class TestFormSubmissionClearsBlankFields:
    async def test_form_blank_hook_line_clears(self, idea_project):
        controller = _make_controller(idea_project)

        class _FormRequest:
            def __init__(self) -> None:
                self.headers = {"content-type": "application/x-www-form-urlencoded"}

            async def form(self):
                return {
                    "project_id": "proj-1",
                    "idea_index": "0",
                    "title": "T",
                    "hook_line": "",
                    "core_message": "Old core",
                    "target_audience": "Old audience",
                }

        await controller.update(request=_FormRequest())
        assert _updates(controller)["hook_line"] == ""
