from unittest.mock import MagicMock

from shorts_creator.controllers.scripts import ScriptsController


class _FakeProject:
    def __init__(self, id="p1", idea_json=None):
        self.id = id
        self.idea_json = idea_json


class FakeIdeaService:
    pass


class FakeScriptService:
    pass


class FakeConfig:
    pass


class FakeProjectService:
    def __init__(self, project_by_id=None):
        self._project_by_id = project_by_id or {}

    async def get(self, project_id):
        return self._project_by_id.get(project_id)

    async def list_recent(self, limit=1):
        return list(self._project_by_id.values())[:limit]


class FakeRunService:
    async def list_by_project(self, project_id, limit=50):
        return []


class TestScriptsStateWiring:
    async def test_page_renders_idea_list_from_state(self):
        project = _FakeProject(
            id="p1",
            idea_json='[{"id": "i1", "title": "First Idea", "core_message": "M", "hook_line": "H", "identity_signal": "I", "permission_given": "P", "emotional_arc": "A", "target_audience": "T", "share_trigger": "S", "quotability_score": 8.0}]',
        )
        controller = ScriptsController(
            scripts=FakeScriptService(),
            ideas=FakeIdeaService(),
            config=FakeConfig(),
            runs=FakeRunService(),
            projects=FakeProjectService(project_by_id={"p1": project}),
        )
        req = MagicMock()
        req.query_params = {}
        html = str(await controller.list_scripts(request=req, id="p1"))
        assert "First Idea" in html
        assert "No ideas generated yet" not in html
