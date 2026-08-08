import asyncio
import json
from pathlib import Path

import pytest

from shorts_creator.controllers.api.ideas_api import IdeasApiController
from shorts_creator.controllers.api.scripts_api import ScriptsApiController
from shorts_creator.controllers.project_settings import ProjectSettingsController
from shorts_creator.controllers.render import render_active_html
from shorts_creator.services.core import AppConfig
from shorts_creator.services.progress_store import ProgressStore

LOG_PANEL_JS = (
    Path(__file__).resolve().parents[1] / "src/shorts_creator/ui/static/js/log-panel.js"
).read_text()


class _FakeRequest:
    def __init__(self, body=None, headers=None):
        self.headers = headers or {"content-type": "application/json"}
        self._body = body or {}

    async def json(self):
        return self._body


class _FakeIdeas:
    def __init__(self, results=None):
        self._results = results or []
        self.calls = []

    async def generate_ideas(
        self,
        count=10,
        focus="all categories",
        topic="self_improvement",
        voice=None,
    ):
        self.calls.append((count, focus, topic))
        return self._results


class _FakeScripts:
    async def generate_script(self, idea):
        return None


class _FakeRepo:
    async def update(self, project):
        pass


class _FakeProject:
    def __init__(self, idea_json):
        self.id = "proj-1"
        self.idea_json = idea_json
        self.repo = _FakeRepo()


class _FakeProjects:
    def __init__(self, idea_json=None):
        self._idea_json = idea_json
        self.saved_scripts = []
        self.prepend_fails = False
        self.save_script_fails = False
        self.updated = []
        self.deleted = []

    async def get(self, project_id):
        if self._idea_json is None:
            return None
        return _FakeProject(self._idea_json)

    async def prepend_ideas(self, project_id, ideas):
        if self.prepend_fails:
            raise RuntimeError("db down")

    async def get_script(self, project_id, idea_id):
        if project_id == "proj-1":
            return {
                "title": "S",
                "sections": [{"name": "hook", "text": "Hi", "duration_seconds": 2.0}],
                "total_duration": 2.0,
                "word_count": 3,
                "pacing_wps": 1.5,
                "emotional_arc": None,
                "metadata": {},
            }
        return None

    async def save_script(self, project_id, idea_id, script):
        if self.save_script_fails:
            raise RuntimeError("disk full")
        self.saved_scripts.append((project_id, idea_id, script))

    async def update_idea(self, project_id, idea_id, updates):
        self.updated.append((project_id, idea_id, updates))

    async def delete_idea(self, project_id, idea_id):
        self.deleted.append((project_id, idea_id))


class _FakeTaskManager:
    def __init__(self):
        self.tasks = []

    def track_named(self, name, coro):
        self.tasks.append((name, coro))

    def close_tasks(self):
        for _, coro in self.tasks:
            if not coro.cr_await and not coro.cr_running:
                coro.close()


def make_ideas_controller(projects=None, tm=None, results=None):
    return IdeasApiController(
        ideas=_FakeIdeas(results=results),
        config=AppConfig(),
        projects=projects or _FakeProjects(),
        progress_store=ProgressStore(),
        task_manager=tm or _FakeTaskManager(),
    )


def make_scripts_controller(projects=None, tm=None):
    return ScriptsApiController(
        scripts=_FakeScripts(),
        ideas=_FakeIdeas(),
        config=AppConfig(),
        runs=None,
        projects=projects or _FakeProjects(),
        progress_store=ProgressStore(),
        task_manager=tm or _FakeTaskManager(),
    )


def drain_queue(store, op_id):
    q = store._queues[op_id]
    events = []
    while not q.empty():
        events.append(q.get_nowait())
    return events


class TestKeepAlive:
    @pytest.mark.asyncio
    async def test_subscribe_stays_alive_across_silence_and_delivers_later_events(self):
        store = ProgressStore()
        store._keep_alive = 0.01
        store.create_queue("op-1")
        store.push("op-1", {"event": "progress", "data": {"stage": "s", "progress": 0.1}})

        received = []

        async def collect():
            async for event in store.subscribe("op-1"):
                received.append(event)
                if isinstance(event, dict) and event.get("event") == "complete":
                    break

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.05)
        store.push("op-1", {"event": "complete", "data": {}})
        await asyncio.wait_for(task, timeout=2)

        assert any(isinstance(e, str) and e.startswith(": keep-alive") for e in received)
        assert any(isinstance(e, dict) and e.get("event") == "complete" for e in received)


class TestConnectErrorFeedback:
    def test_lp_connect_fires_on_done_on_connection_loss(self):
        assert "function finish(err, evt)" in LOG_PANEL_JS
        assert "if (settled) return;" in LOG_PANEL_JS
        assert "finish(new Error('Connection lost'), null);" in LOG_PANEL_JS
        assert "finish(null, e);" in LOG_PANEL_JS
        assert "finish(new Error(d && d.error || 'Failed'), e);" in LOG_PANEL_JS


class TestRenderSseReconnect:
    def test_render_active_html_reconnects_then_falls_back(self):
        html = render_active_html("run-abc")
        assert "var attempts = 0;" in html
        assert "setTimeout(connect, Math.min(1000 * attempts, 5000))" in html
        assert "if (attempts < 5)" in html
        assert "htmx.ajax('GET', '/projects?run_id=run-abc'" in html
        assert "function connect()" in html

    def test_render_active_html_uses_project_scoped_url(self):
        html = render_active_html("run-abc", project_id="proj-1")
        assert "htmx.ajax('GET', '/projects/proj-1/render?run_id=run-abc'" in html
        assert "pushUrl: '/projects/proj-1/render?run_id=run-abc'" in html


class TestIdeasGenerateSaveFailure:
    @pytest.mark.asyncio
    async def test_prepend_failure_marks_op_failed(self):
        tm = _FakeTaskManager()
        projects = _FakeProjects(idea_json=json.dumps([]))
        projects.prepend_fails = True
        controller = make_ideas_controller(projects=projects, tm=tm, results=[])

        await controller.generate(request=_FakeRequest({"project_id": "proj-1"}))
        try:
            name, coro = tm.tasks[0]
            assert name.startswith("ideas:")
            await coro
            events = drain_queue(controller.progress_store, name.split(":", 1)[1])
            assert events[-1]["event"] == "failed"
            assert "db down" in events[-1]["data"]["error"]
        finally:
            tm.close_tasks()


class TestIdeaUpdateToastOnlyOnChange:
    @pytest.mark.asyncio
    async def test_empty_update_no_false_toast(self):
        controller = make_ideas_controller(
            projects=_FakeProjects(
                idea_json=json.dumps(
                    [
                        {
                            "id": "i1",
                            "title": "T",
                            "core_message": "M",
                            "hook_line": "H",
                            "identity_signal": "I",
                            "permission_given": "P",
                            "emotional_arc": "E",
                            "target_audience": "A",
                            "quotability_score": 8.0,
                            "share_trigger": "S",
                        }
                    ]
                )
            )
        )
        html = str(
            await controller.update(request=_FakeRequest({"project_id": "proj-1", "idea_index": 0}))
        )
        assert "Idea saved" not in html

    @pytest.mark.asyncio
    async def test_real_update_shows_toast(self):
        projects = _FakeProjects(
            idea_json=json.dumps(
                [
                    {
                        "id": "i1",
                        "title": "T",
                        "core_message": "M",
                        "hook_line": "H",
                        "identity_signal": "I",
                        "permission_given": "P",
                        "emotional_arc": "E",
                        "target_audience": "A",
                        "quotability_score": 8.0,
                        "share_trigger": "S",
                    }
                ]
            )
        )
        controller = make_ideas_controller(projects=projects)
        html = str(
            await controller.update(
                request=_FakeRequest(
                    {"project_id": "proj-1", "idea_index": 0, "title": "New Title"}
                )
            )
        )
        assert "Idea saved" in html
        assert projects.updated == [("proj-1", "i1", {"title": "New Title"})]


class TestIdeaDeleteToastOnlyOnChange:
    @pytest.mark.asyncio
    async def test_delete_missing_idea_no_false_toast(self):
        projects = _FakeProjects(
            idea_json=json.dumps(
                [
                    {
                        "id": "i1",
                        "title": "T",
                        "core_message": "M",
                        "hook_line": "H",
                        "identity_signal": "I",
                        "permission_given": "P",
                        "emotional_arc": "E",
                        "target_audience": "A",
                        "quotability_score": 8.0,
                        "share_trigger": "S",
                    }
                ]
            )
        )
        controller = make_ideas_controller(projects=projects)
        html = str(
            await controller.delete(request=_FakeRequest({"project_id": "proj-1", "idea_index": 5}))
        )
        assert "Idea deleted" not in html
        assert projects.deleted == []

    @pytest.mark.asyncio
    async def test_real_delete_shows_toast(self):
        projects = _FakeProjects(
            idea_json=json.dumps(
                [
                    {
                        "id": "i1",
                        "title": "T",
                        "core_message": "M",
                        "hook_line": "H",
                        "identity_signal": "I",
                        "permission_given": "P",
                        "emotional_arc": "E",
                        "target_audience": "A",
                        "quotability_score": 8.0,
                        "share_trigger": "S",
                    }
                ]
            )
        )
        controller = make_ideas_controller(projects=projects)
        html = str(
            await controller.delete(request=_FakeRequest({"project_id": "proj-1", "idea_index": 0}))
        )
        assert "Idea deleted" in html
        assert projects.deleted == [("proj-1", "i1")]


class TestSectionSaveFailurePreservesEditor:
    @pytest.mark.asyncio
    async def test_failure_keeps_wrapper_and_shows_error_toast(self):
        projects = _FakeProjects(
            idea_json=json.dumps(
                [
                    {
                        "id": "i1",
                        "title": "T",
                        "core_message": "M",
                        "hook_line": "H",
                        "identity_signal": "I",
                        "permission_given": "P",
                        "emotional_arc": "E",
                        "target_audience": "A",
                        "quotability_score": 8.0,
                        "share_trigger": "S",
                    }
                ]
            )
        )
        projects.save_script_fails = True
        controller = make_scripts_controller(projects=projects)
        html = str(
            await controller.update_section(
                request=_FakeRequest(
                    {
                        "project_id": "proj-1",
                        "idea_index": 0,
                        "section_name": "hook",
                        "text": "edited text",
                    }
                )
            )
        )
        assert 'id="sec-wrapper-hook-0"' in html
        assert "edited text" in html
        assert "Save failed: disk full" in html
        assert "window.showToast" in html

    @pytest.mark.asyncio
    async def test_success_toast(self):
        projects = _FakeProjects(
            idea_json=json.dumps(
                [
                    {
                        "id": "i1",
                        "title": "T",
                        "core_message": "M",
                        "hook_line": "H",
                        "identity_signal": "I",
                        "permission_given": "P",
                        "emotional_arc": "E",
                        "target_audience": "A",
                        "quotability_score": 8.0,
                        "share_trigger": "S",
                    }
                ]
            )
        )
        controller = make_scripts_controller(projects=projects)
        html = str(
            await controller.update_section(
                request=_FakeRequest(
                    {
                        "project_id": "proj-1",
                        "idea_index": 0,
                        "section_name": "hook",
                        "text": "new text",
                    }
                )
            )
        )
        assert "Section saved" in html
        assert "Save failed" not in html


class TestSeoSave:
    @pytest.mark.asyncio
    async def test_success_persists_and_swaps_wrapper(self):
        projects = _FakeProjects(idea_json=json.dumps([]))
        controller = make_scripts_controller(projects=projects)
        html = str(
            await controller.update_seo(
                request=_FakeRequest(
                    {
                        "project_id": "proj-1",
                        "idea_id": "idea-1",
                        "key": "youtube_title",
                        "text": "Edited SEO title",
                    }
                )
            )
        )
        assert "SEO saved" in html
        assert 'id="seo-wrapper-youtube_title-idea-1"' in html
        assert "Edited SEO title" in html
        assert projects.saved_scripts == [
            (
                "proj-1",
                "idea-1",
                {
                    "title": "S",
                    "sections": [{"name": "hook", "text": "Hi", "duration_seconds": 2.0}],
                    "total_duration": 2.0,
                    "word_count": 3,
                    "pacing_wps": 1.5,
                    "emotional_arc": None,
                    "metadata": {"seo": {"youtube_title": "Edited SEO title"}},
                },
            )
        ]

    @pytest.mark.asyncio
    async def test_unknown_key_rejected(self):
        projects = _FakeProjects(idea_json=json.dumps([]))
        controller = make_scripts_controller(projects=projects)
        html = str(
            await controller.update_seo(
                request=_FakeRequest(
                    {
                        "project_id": "proj-1",
                        "idea_id": "idea-1",
                        "key": "instagram_bio",
                        "text": "x",
                    }
                )
            )
        )
        assert "Missing fields" in html
        assert projects.saved_scripts == []

    @pytest.mark.asyncio
    async def test_failure_keeps_wrapper_and_shows_error_toast(self):
        projects = _FakeProjects(idea_json=json.dumps([]))
        projects.save_script_fails = True
        controller = make_scripts_controller(projects=projects)
        html = str(
            await controller.update_seo(
                request=_FakeRequest(
                    {
                        "project_id": "proj-1",
                        "idea_id": "idea-1",
                        "key": "facebook_caption",
                        "text": "new caption",
                    }
                )
            )
        )
        assert 'id="seo-wrapper-facebook_caption-idea-1"' in html
        assert "new caption" in html
        assert "Save failed: disk full" in html


class TestMissingProject404:
    @pytest.mark.asyncio
    async def test_save_project_settings_returns_404_not_500(self):
        controller = ProjectSettingsController(
            config=AppConfig(),
            projects=_FakeProjects(),
            store=None,
        )
        resp = await controller.save_project_settings(request=None, id="missing")
        assert resp.status_code == 404
