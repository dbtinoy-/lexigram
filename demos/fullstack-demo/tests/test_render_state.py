from unittest.mock import MagicMock

from shorts_creator.controllers.render import RenderController


class _FakeProject:
    def __init__(self, id="p1", idea_json=None, topic="self_improvement"):
        self.id = id
        self.idea_json = idea_json
        self.topic = topic


class FakeIdeaService:
    pass


class FakeScriptService:
    _last_script = None

    @property
    def last_script(self):
        return self._last_script


class FakeConfig:
    reel_width = 1080
    reel_height = 1920
    default_duration = 30


class FakeProjectService:
    def __init__(self, project=None):
        self._project = project

    async def get(self, project_id):
        return self._project


class FakeRunService:
    async def list_by_project(self, project_id, limit=50):
        return []


class FakeSettingsStore:
    async def get_overrides(self):
        return {}


class TestRenderStateWiring:
    async def test_render_page_renders_with_idea_script(self):
        project = _FakeProject(
            idea_json='[{"id": "i1", "title": "Idea One", "core_message": "M", '
            '"script_json": "{\\"title\\": \\"S\\", \\"sections\\": [], \\"total_duration\\": 30, \\"word_count\\": 120}"}]'
        )
        controller = RenderController(
            ideas=FakeIdeaService(),
            scripts=FakeScriptService(),
            config=FakeConfig(),
            runs=FakeRunService(),
            project_service=FakeProjectService(project),
            store=FakeSettingsStore(),
        )
        req = MagicMock()
        req.query_params = {"idea_index": "0"}
        html = str(await controller.render_page(request=req, id="p1"))
        assert "Render Engine Studio" in html
        assert "No video rendered yet" in html

    async def test_specs_tab_links_to_project_settings(self):
        project = _FakeProject(
            idea_json='[{"id": "i1", "title": "Idea One", "core_message": "M", '
            '"script_json": "{\\"title\\": \\"S\\", \\"sections\\": [], \\"total_duration\\": 30, \\"word_count\\": 120}"}]'
        )
        controller = RenderController(
            ideas=FakeIdeaService(),
            scripts=FakeScriptService(),
            config=FakeConfig(),
            runs=FakeRunService(),
            project_service=FakeProjectService(project),
            store=FakeSettingsStore(),
        )
        req = MagicMock()
        req.query_params = {"idea_index": "0"}
        html = str(await controller.render_page(request=req, id="p1"))
        assert "Project Settings →" in html
        assert 'href="/projects/p1/settings"' in html
        assert "Composer →" not in html

    async def test_render_page_renders_with_run_id_query(self):
        project = _FakeProject(idea_json='[{"id": "i1", "title": "Idea One", "core_message": "M"}]')

        controller = RenderController(
            ideas=FakeIdeaService(),
            scripts=FakeScriptService(),
            config=FakeConfig(),
            runs=FakeRunService(),
            project_service=FakeProjectService(project),
            store=FakeSettingsStore(),
        )
        req = MagicMock()
        req.query_params = {"run_id": "r99"}
        html = str(await controller.render_page(request=req, id="p1"))
        assert "Render Engine Studio" in html

    async def test_render_page_redirects_when_no_project_id(self):
        controller = RenderController(
            ideas=FakeIdeaService(),
            scripts=FakeScriptService(),
            config=FakeConfig(),
            runs=FakeRunService(),
            project_service=FakeProjectService(),
            store=FakeSettingsStore(),
        )
        req = MagicMock()
        req.query_params = {"run_id": "r99"}
        resp = await controller.render_page(request=req, id="")
        assert getattr(resp, "status_code", None) == 302
