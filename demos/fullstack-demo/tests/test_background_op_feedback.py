import asyncio
import json

from shorts_creator.controllers.api.ideas_api import IdeasApiController
from shorts_creator.controllers.api.scripts_api import ScriptsApiController
from shorts_creator.services.core import AppConfig
from shorts_creator.services.progress_store import ProgressStore
from shorts_creator.topics.base import ParsedScript


class _FakeRequest:
    def __init__(self, body=None, headers=None):
        self.headers = headers or {"content-type": "application/json"}
        self._body = body or {}

    async def json(self):
        return self._body


class _FakeIdeas:
    def __init__(self):
        self.calls = []

    async def generate_ideas(
        self,
        count=10,
        focus="all categories",
        topic="self_improvement",
        voice=None,
    ):
        self.calls.append((count, focus, topic))
        return []


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

    async def get(self, project_id):
        if self._idea_json is None:
            return None
        return _FakeProject(self._idea_json)

    async def prepend_ideas(self, project_id, ideas):
        pass

    async def save_script(self, project_id, idea_id, script):
        pass


class _FakeScripts:
    async def generate_script(self, idea, format_name="", pacing_wps=None, voice=None):
        return None


class _FakeTaskManager:
    def __init__(self):
        self.tasks = []

    def track_named(self, name, coro):
        self.tasks.append((name, coro))

    def close_tasks(self):
        for _, coro in self.tasks:
            coro.close()


class _RunningTaskManager(_FakeTaskManager):
    def track_named(self, name, coro):
        super().track_named(name, coro)
        self.task = asyncio.ensure_future(coro)


class _PacingScripts:
    def __init__(self):
        self.calls = []

    async def generate_script(self, idea, format_name="", pacing_wps=None, voice=None):
        self.calls.append((format_name, pacing_wps))
        return ParsedScript(
            title="T",
            sections=[],
            total_duration=10.0,
            word_count=10,
            pacing_wps=2.5,
        )


class _PacingProfileService:
    def __init__(self, value):
        self._value = value

    async def resolve(self, project):
        from shorts_creator.models.project_profile import (
            EffectiveProjectProfile,
            ProfileSource,
            ResolvedSetting,
        )

        return EffectiveProjectProfile(
            pacing_wps=ResolvedSetting(self._value, ProfileSource.PROJECT, True),
        )


class _ProjectWithFormat(_FakeProject):
    def __init__(self, idea_json):
        super().__init__(idea_json)
        self.format = "narrated"


class _ProjectsWithFormat(_FakeProjects):
    async def get(self, project_id):
        if self._idea_json is None:
            return None
        return _ProjectWithFormat(self._idea_json)


class TestBackgroundOpButtonFeedback:
    async def test_ideas_generate_disables_fired_button_and_refreshes_on_error(self):
        tm = _FakeTaskManager()
        controller = IdeasApiController(
            ideas=_FakeIdeas(),
            config=AppConfig(),
            projects=_FakeProjects(),
            progress_store=ProgressStore(),
            task_manager=tm,
        )
        html = str(
            await controller.generate(request=_FakeRequest({"topic": "viral", "project_id": ""}))
        )
        try:
            assert 'button[hx-post="/api/ideas/generate"]' in html
            assert "btn.classList.add('busy')" in html
            assert "btn.setAttribute('aria-disabled', 'true')" in html
            assert "htmx:afterRequest" in html
            assert "e.detail.elt === btn" in html
            assert "Idea generation failed" in html
            assert "htmx.ajax('GET'" in html
        finally:
            tm.close_tasks()

    async def test_scripts_generate_disables_fired_button_and_refreshes_on_error(self):
        tm = _FakeTaskManager()
        idea_json = json.dumps(
            [
                {
                    "id": "idea-1",
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
        controller = ScriptsApiController(
            scripts=_FakeScripts(),
            ideas=_FakeIdeas(),
            config=AppConfig(),
            runs=None,
            projects=_FakeProjects(idea_json=idea_json),
            progress_store=ProgressStore(),
            task_manager=tm,
        )
        html = str(
            await controller.generate(
                request=_FakeRequest({"idea_index": 0, "project_id": "proj-1"})
            )
        )
        try:
            assert 'button[hx-post="/api/scripts/generate"]' in html
            assert "btn.classList.add('busy')" in html
            assert "btn.setAttribute('aria-disabled', 'true')" in html
            assert "htmx:afterRequest" in html
            assert "e.detail.elt === btn" in html
            assert "Script generation failed" in html
            assert "htmx.ajax('GET'" in html
        finally:
            tm.close_tasks()


class TestGenerateScriptPacing:
    async def test_profile_pacing_reaches_generate_script(self):
        tm = _RunningTaskManager()
        scripts = _PacingScripts()
        controller = ScriptsApiController(
            scripts=scripts,
            ideas=_FakeIdeas(),
            config=AppConfig(),
            runs=None,
            projects=_ProjectsWithFormat(
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
            ),
            progress_store=ProgressStore(),
            task_manager=tm,
            profile_service=_PacingProfileService(2.5),
        )
        await controller.generate(request=_FakeRequest({"idea_index": 0, "project_id": "proj-1"}))
        await asyncio.wait_for(asyncio.shield(tm.task), timeout=5)

        assert scripts.calls == [("narrated", 2.5)]

    async def test_no_profile_service_leaves_pacing_none(self):
        tm = _RunningTaskManager()
        scripts = _PacingScripts()
        controller = ScriptsApiController(
            scripts=scripts,
            ideas=_FakeIdeas(),
            config=AppConfig(),
            runs=None,
            projects=_ProjectsWithFormat(
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
            ),
            progress_store=ProgressStore(),
            task_manager=tm,
        )
        await controller.generate(request=_FakeRequest({"idea_index": 0, "project_id": "proj-1"}))
        await asyncio.wait_for(asyncio.shield(tm.task), timeout=5)

        assert scripts.calls == [("narrated", None)]
