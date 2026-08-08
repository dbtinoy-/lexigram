"""Regression tests for double-escaped HTML.

Builders that render pre-built HTML via ``el()`` must return ``Markup`` so
that embedding them as ``el()`` children does not escape their markup a
second time (visible as literal ``&lt;div&gt;`` text in the browser).
"""

import json
from unittest.mock import MagicMock

from lexigram.web import HTMLContent

from shorts_creator.controllers.project_runs import ProjectRunsController
from shorts_creator.controllers.scripts import ScriptsController
from shorts_creator.models.project import Project
from shorts_creator.models.run import Run, RunStatus
from shorts_creator.ui.components.concept_list_item import ConceptListItem, IdeaEditForm
from shorts_creator.ui.components.pipeline_tracker import PipelineTracker
from shorts_creator.ui.components.run_history import RunHistoryTable

SCRIPT_JSON = {
    "title": "Morning Hack",
    "sections": [
        {"name": "hook", "text": "You are overcomplicating it.", "duration_seconds": 3.0},
        {"name": "body", "text": "Here is the fix.", "duration_seconds": 10.0},
    ],
    "total_duration": 13.0,
    "word_count": 40,
    "pacing_wps": 3.1,
    "emotional_arc": [],
    "metadata": {},
}


def _project(idea_json=None) -> Project:
    return Project(id="p1", topic="discipline", title="Proj", idea_json=idea_json)


def _idea(i: int, with_script: bool = False) -> dict:
    d = {
        "id": f"idea-{i}",
        "title": f"Idea {i}",
        "core_message": f"Core {i}",
        "hook_line": f"Hook {i}",
        "identity_signal": "",
        "permission_given": "",
        "emotional_arc": "",
        "target_audience": "",
        "share_trigger": f"Share {i}",
        "quotability_score": 8.0,
    }
    if with_script:
        d["script_json"] = json.dumps(SCRIPT_JSON)
    return d


def _ideas_json(n: int, with_script: int = 0) -> str:
    return json.dumps([_idea(i, i < with_script) for i in range(n)])


class _FakeRuns:
    def __init__(self, runs=None):
        self.runs = runs or []

    async def get(self, run_id):
        return next((r for r in self.runs if r.id == run_id), None)

    async def list_recent(self, limit=200):
        return self.runs[:limit]

    async def list_status(self, status, limit=10_000):
        return [r for r in self.runs if r.status == status]

    async def list_by_project(self, project_id, limit=50):
        return [r for r in self.runs if r.project_id == project_id]


class _FakeProjects:
    def __init__(self, projects=None):
        self.projects = projects or {}

    async def get(self, project_id):
        return self.projects.get(project_id)


class _FakeLayout:
    def render(self, content="", title="", request=None):
        return f"<html>{title}|{content}</html>"


class _FakeScriptService:
    async def get_all(self):
        return []

    async def get(self, script_id):
        return None


class _FakeIdeaService:
    async def all(self):
        return []

    async def get(self, idea_id):
        return None


class _FakeConfig:
    pass


def _assert_no_escaped_markup(body: str):
    assert "&lt;" not in body, f"Escaped markup leak detected: {body}"
    assert "&amp;lt;" not in body


class TestScriptsPageEscaping:
    def _render(self, project, run=None, idea_index=None, sort="", page="", runs_service=None):
        c = ScriptsController(
            scripts=_FakeScriptService(),
            ideas=_FakeIdeaService(),
            config=_FakeConfig(),
            runs=runs_service or _FakeRuns(),
            projects=_FakeProjects({project.id: project}),
        )
        c.layout = _FakeLayout()
        req = MagicMock()
        req.query_params = {
            "idea_index": str(idea_index) if idea_index is not None else "",
            "sort": sort,
            "page": str(page),
        }

        async def _go():
            resp = await c.list_scripts(request=req, id=project.id)
            if isinstance(resp, (str, HTMLContent)):
                return str(resp)
            body = resp.body if hasattr(resp, "body") else str(resp)
            return body.decode() if isinstance(body, bytes) else body

        import asyncio

        return asyncio.run(_go())

    def test_selected_script_renders_real_markup(self):
        project = _project(_ideas_json(3, with_script=2))
        body = self._render(project, idea_index=1)
        _assert_no_escaped_markup(body)
        assert 'href="/projects/p1/render?idea_index=1"' in body
        assert "Morning Hack" in body
        assert "You are overcomplicating it." in body

    def test_pagination_renders_links(self):
        project = _project(_ideas_json(12))
        body = self._render(project, page=1)
        _assert_no_escaped_markup(body)
        assert "Page 2 of 2" in body or "of 2" in body

    def test_concept_list_renders_markup(self):
        project = _project(_ideas_json(2, with_script=1))
        body = self._render(project)
        _assert_no_escaped_markup(body)
        assert "Idea 1" in body


class TestRunPanelEscaping:
    def test_partial_panel_renders_real_markup(self):
        run = Run(
            id="r1",
            project_id="p1",
            title="Morning Run",
            status=RunStatus.SCRIPT_READY,
            selected_idea_id="idea-0",
            duration_s=13.0,
        )
        project = _project(_ideas_json(2, with_script=1))
        c = ProjectRunsController(projects=_FakeProjects({"p1": project}), runs=_FakeRuns([run]))
        c.layout = _FakeLayout()
        req = MagicMock()
        req.query_params = {"partial": "1"}

        async def _go():
            resp = await c.run_detail(request=req, pid="p1", rid="r1")
            return resp.body if hasattr(resp, "body") else str(resp)

        import asyncio

        body = asyncio.run(_go())
        _assert_no_escaped_markup(body)
        assert "Morning Hack" in body
        assert "Idea 0" in body

    def test_full_dashboard_renders_real_markup(self):
        run = Run(
            id="r2",
            project_id="p1",
            title="Failed Run",
            status=RunStatus.FAILED,
            error="boom",
        )
        project = _project(_ideas_json(1, with_script=1))
        c = ProjectRunsController(projects=_FakeProjects({"p1": project}), runs=_FakeRuns([run]))
        c.layout = _FakeLayout()
        req = MagicMock()
        req.query_params = {}

        async def _go():
            resp = await c.run_detail(request=req, pid="p1", rid="r2")
            return resp.body if hasattr(resp, "body") else str(resp)

        import asyncio

        body = asyncio.run(_go())
        _assert_no_escaped_markup(body)
        assert "Failed" in body or "failed" in body


class TestComponentEscaping:
    def test_pipeline_tracker(self):
        _assert_no_escaped_markup(
            str(
                PipelineTracker(
                    current="script",
                    project_id="p1",
                    stage_state=[
                        {"done": True, "active": False, "preview": "2 ideas"},
                        {"done": False, "active": True, "preview": "Morning Hack"},
                        {"done": False, "active": False, "preview": ""},
                    ],
                )
            )
        )

    def test_concept_list_item(self):
        item = ConceptListItem(
            type(
                "Idea",
                (),
                {
                    "title": "Morning Hack",
                    "quotability_score": 8.5,
                    "hook_line": "Hook",
                    "target_audience": "",
                    "core_message": "Core",
                    "identity_signal": "",
                    "permission_given": "",
                },
            )(),
            1,
            idea_index=0,
            project_id="p1",
            selected=True,
            has_script=True,
            has_video=False,
        )
        _assert_no_escaped_markup(str(item))
        assert 'id="concept-0"' in str(item)

    def test_idea_edit_form(self):
        form = IdeaEditForm(
            type(
                "Idea",
                (),
                {
                    "title": "Editable",
                    "quote": "",
                    "quotability_score": 7.0,
                    "hook_line": "H",
                    "target_audience": "",
                    "core_message": "C",
                },
            )(),
            0,
            project_id="p1",
        )
        _assert_no_escaped_markup(str(form))
        assert "Editable" in str(form)

    def test_run_history_table(self):
        html = str(
            RunHistoryTable(
                [
                    {
                        "created_at": "2026-01-01T10:00:00",
                        "idea": "Morning Hack",
                        "status": "completed",
                        "output": "/tmp/x.mp4",
                        "duration_s": 9.5,
                        "project_id": "p1",
                    },
                ],
                expandable=True,
                projects={"p1": "Proj"},
            )
        )
        _assert_no_escaped_markup(html)
        assert "Morning Hack" in html
        assert "Completed" in html


class TestTopicsChipsEscaping:
    def test_edit_topic_renders_structure_chips(self):
        from types import SimpleNamespace

        from shorts_creator.controllers.topics import TopicsController

        profile = SimpleNamespace(
            structure_sections=["Hook", "Body", "CTA"],
            topic_categories=["cats"],
            banned_phrases=[],
            background_queries=[],
            idea_prompt="" if False else None,
            script_prompt=None,
        )

        class _FakeProfileService:
            async def get(self, name):
                return profile

            async def list(self):
                return []

        c = TopicsController(_FakeProfileService())
        c.layout = _FakeLayout()

        import asyncio

        resp = asyncio.run(c.edit_topic(request=None, name="discipline"))
        body = resp.body if hasattr(resp, "body") else str(resp)
        _assert_no_escaped_markup(body)
        assert "Hook" in body
        assert "CTA" in body


class TestHistoryStatTilesEscaping:
    def test_stat_tiles_render_real_markup(self):
        from lexigram.ui import el, render_to_string

        from shorts_creator.controllers.history import _StatTile
        from shorts_creator.ui.icons import clock

        html = render_to_string(
            el(
                "div",
                _StatTile("Ideas", "3", clock, "text-primary", href="/projects"),
                _StatTile("Total Runs", "7", clock, "text-success"),
            )
        )
        _assert_no_escaped_markup(html)
        assert 'href="/projects"' in html
        assert "Total Runs" in html


class TestAssetsGeneratedTabEscaping:
    def test_generated_tab_renders_real_markup(self, tmp_path):

        from shorts_creator.controllers.assets import AssetsController

        v = tmp_path / "clip.mp4"
        v.write_bytes(b"x")
        run = Run(
            id="v1",
            project_id="p1",
            title="Morning Routine",
            status=RunStatus.COMPLETED,
            output_path=str(v),
            duration_s=34.5,
        )

        class _FakeService:
            async def get(self, asset_id):
                return None

            async def list_all(self):
                return []

        class _FakeRuns2:
            def __init__(self, runs):
                self.runs = runs

            async def list_status(self, status, limit=10_000):
                return [r for r in self.runs if r.status == status]

        class _FakeProjects2:
            def __init__(self, projects):
                self.projects = projects

            async def get(self, project_id):
                return self.projects.get(project_id)

        c = AssetsController(
            _FakeService(), runs=_FakeRuns2([run]), projects=_FakeProjects2({"p1": _project()})
        )
        c.layout = _FakeLayout()
        req = MagicMock()
        req.query_params = {"tab": "generated"}

        import asyncio

        resp = asyncio.run(c.library(request=req))
        body = resp.body if hasattr(resp, "body") else str(resp)
        _assert_no_escaped_markup(body)
        assert "Morning Routine" in body
        assert "/api/videos/download/v1" in body


class TestHistoryFilterPillEscaping:
    def test_filter_pills_render_real_markup(self):
        from lexigram.ui import el, render_to_string

        from shorts_creator.controllers.history import _FilterPill

        html = render_to_string(
            el("div", _FilterPill("completed", "failed", 3), _FilterPill("all", "failed", 12))
        )
        _assert_no_escaped_markup(html)
        assert 'href="/history?status=completed"' in html
        assert ">3<" in html or "3</span>" in html


class TestRenderPageComponentsEscaping:
    def test_render_accordion_helpers_emit_clean_markup(self):
        from lexigram.ui import el, render_to_string

        from shorts_creator.controllers.render import (
            _PipelineConfig,
            _PipelineStages,
            _RenderButton,
            _RenderEmptyState,
        )

        config = type(
            "Cfg", (), {"reel_height": 1920, "reel_width": 1080, "default_duration": 45}
        )()
        html = render_to_string(
            el(
                "div",
                _PipelineStages([("a", "Ideas", "Pick"), ("b", "Render", "Export")]),
                _RenderButton("script-obj", None, project_id="p1"),
                _RenderEmptyState("script-obj", [], project_id="p1"),
                _PipelineConfig(config, None, project_id="p1"),
            )
        )
        _assert_no_escaped_markup(html)
        assert "Pick" in html or "Ideas" in html


class TestAssetLibraryCardsEscaping:
    def test_library_cards_render_real_markup(self):
        from lexigram.ui import el, render_to_string

        from shorts_creator.controllers.assets import _card
        from shorts_creator.models.asset import Asset

        card = _card(Asset(type="music", name="Lo-fi", file_path="music/1.mp3"))
        html = render_to_string(el("div", card))
        _assert_no_escaped_markup(html)
        assert "Lo-fi" in html
