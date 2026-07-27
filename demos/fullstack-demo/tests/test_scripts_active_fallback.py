import json

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
    pass


class TestScriptsProjectIdFallback:
    async def test_uses_project_when_project_id_given(self):
        project = _FakeProject(id="p1", idea_json="[]")
        controller = ScriptsController(
            scripts=FakeScriptService(),
            ideas=FakeIdeaService(),
            config=FakeConfig(),
            runs=FakeRunService(),
            projects=FakeProjectService(project_by_id={"p1": project}),
        )
        html = await controller.list_scripts(request=None, id="p1")
        assert "p1" in str(html)

    async def test_redirects_to_projects_when_no_project_id(self):
        controller = ScriptsController(
            scripts=FakeScriptService(),
            ideas=FakeIdeaService(),
            config=FakeConfig(),
            runs=FakeRunService(),
            projects=FakeProjectService(),
        )
        response = await controller.list_scripts(request=None, id="")
        assert response.status_code == 302
        assert response.headers["location"] == "/projects"

    async def test_script_actions_link_to_render_only(self):
        project = _FakeProject(
            id="p1",
            idea_json=json.dumps(
                [
                    {
                        "id": "i1",
                        "title": "Idea",
                        "core_message": "Msg",
                        "script_json": json.dumps(
                            {
                                "title": "S",
                                "sections": [],
                                "total_duration": 30,
                                "word_count": 120,
                                "pacing_wps": 2.5,
                            }
                        ),
                    }
                ]
            ),
        )
        controller = ScriptsController(
            scripts=FakeScriptService(),
            ideas=FakeIdeaService(),
            config=FakeConfig(),
            runs=FakeRunService(),
            projects=FakeProjectService(project_by_id={"p1": project}),
        )
        from unittest.mock import MagicMock

        req = MagicMock()
        req.query_params = {"idea_index": "0"}
        html = str(await controller.list_scripts(request=req, id="p1"))
        assert 'href="/projects/p1/compose"' not in html
        assert "Composer" not in html
        assert "Proceed to Render" in html
