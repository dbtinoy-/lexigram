import json
import os
import subprocess
import tempfile

import pytest

from shorts_creator.controllers.api.render_api import RenderApiController, probe_duration
from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProfileSource,
    ResolvedSetting,
)
from shorts_creator.models.run import Run
from shorts_creator.services.core import AppConfig
from shorts_creator.services.run_service import RunService


def _make_video(path: str, duration: float = 2.0) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=blue:d={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}",
            "-shortest",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            path,
        ],
        capture_output=True,
        check=True,
    )


class TestProbeDuration:
    def test_returns_actual_file_duration(self):
        fd, path = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        _make_video(path, duration=2.0)
        try:
            duration = probe_duration(path)
            assert 1.5 <= duration <= 2.5
        finally:
            os.unlink(path)

    def test_missing_file_returns_zero(self):
        assert probe_duration("/nonexistent/never.mp4") == 0.0


class _FakeProject:
    id = "p1"
    topic = "self_improvement"
    idea_json = json.dumps(
        [
            {
                "id": "i1",
                "title": "Idea One",
                "core_message": "M",
                "script_json": json.dumps(
                    {"title": "S", "sections": [], "total_duration": 30, "word_count": 10}
                ),
            }
        ]
    )
    profile_overrides_json = None


class _FakeProjectService:
    async def get(self, project_id):
        return _FakeProject()


class _FakeProfileService:
    def __init__(self, profile):
        self._profile = profile

    async def resolve(self, project):
        return self._profile

    @staticmethod
    def validate(profile):
        return {}

    async def validate_pair_for_project(self, project):
        return []


class _FakeRunRepo:
    def __init__(self):
        self.store = {}

    async def create(self, run):
        self.store[run.id] = run
        return run

    async def update(self, run):
        self.store[run.id] = run
        return run

    async def get(self, run_id):
        return self.store.get(run_id)

    async def list_by_project(self, project_id, limit=50):
        return [r for r in self.store.values() if r.project_id == project_id][:limit]


class _FakeTask:
    def done(self):
        return True


class _FakeTaskManager:
    def track_named(self, name, coro):
        coro.close()
        return _FakeTask()


class _FakeHistory:
    async def get_recent(self, limit=3):
        return []


class _FakeScriptService:
    last_script = None


class _NoiseStore:
    """Store that fails if the render API consults a second settings source.

    Credentials (stock-video keys) are the one allowed exception; the store
    here reports none configured.
    """

    async def get_overrides(self):
        raise AssertionError("start_render must not read the settings store")

    async def get_credentials(self):
        return {}


from typing import ClassVar


class _PipelineSpy:
    instances: ClassVar[list] = []

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        _PipelineSpy.instances.append(kwargs)


class _Request:
    def __init__(self, form_data=None):
        self.headers = {"content-type": "application/x-www-form-urlencoded"}
        self._form = form_data or {}

    async def form(self):
        return self._form


def _profile(duration: int = 45) -> EffectiveProjectProfile:
    return EffectiveProjectProfile(
        duration_seconds=ResolvedSetting(duration, ProfileSource.PROJECT, True),
        caption_style=ResolvedSetting("plain", ProfileSource.FORMAT, False),
        reel_width=ResolvedSetting(720, ProfileSource.BUILT_IN, False),
        reel_height=ResolvedSetting(1280, ProfileSource.BUILT_IN, False),
    )


def _make_controller(profile_service, runs=None, store=None):
    return RenderApiController(
        scripts=_FakeScriptService(),
        ideas=None,
        history=_FakeHistory(),
        project_service=_FakeProjectService(),
        task_manager=_FakeTaskManager(),
        config=AppConfig(),
        runs=runs or RunService(repo=_FakeRunRepo()),
        store=store if store is not None else _NoiseStore(),
        profile_service=profile_service,
    )


class TestStartRenderResolvesDurationOnce:
    @pytest.mark.parametrize("profile_duration", [45, 60])
    async def test_pipeline_gets_snapshot_duration(self, monkeypatch, profile_duration):
        _PipelineSpy.instances = []
        controller = _make_controller(_FakeProfileService(_profile(profile_duration)))
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        await controller.start_render(request=_Request({"project_id": "p1", "idea_index": "0"}))
        captured = _PipelineSpy.instances[-1]
        assert captured["duration_seconds"] == profile_duration
        assert captured["reel_width"] == 720
        assert captured["reel_height"] == 1280
        assert captured["caption_style"] == "plain"
        assert captured["duration_seconds"] != controller.config.default_duration

    async def test_existing_run_snapshot_wins_over_fresh_profile(self, monkeypatch):
        _PipelineSpy.instances = []
        runs = RunService(repo=_FakeRunRepo())
        run = await runs.repo.create(Run(project_id="p1"))
        await runs.update_profile_snapshot(
            run.id,
            {
                "duration_seconds": 90,
                "caption_style": "highlight",
                "reel_width": 360,
                "reel_height": 640,
            },
        )
        controller = _make_controller(_FakeProfileService(_profile(45)), runs=runs)
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        await controller.start_render(
            request=_Request({"project_id": "p1", "run_id": run.id, "idea_index": "0"})
        )
        captured = _PipelineSpy.instances[-1]
        assert captured["duration_seconds"] == 90
        assert captured["caption_style"] == "highlight"
        assert captured["reel_width"] == 360
        assert captured["reel_height"] == 640
        first_store_read = await runs.get_snapshot(run.id)
        assert first_store_read["duration_seconds"] == 90

    async def test_invalid_profile_aborts_before_run_creation(self, monkeypatch):
        _PipelineSpy.instances = []

        class InvalidProfileService(_FakeProfileService):
            @staticmethod
            def validate(profile):
                return {"duration_seconds": "must be greater than zero"}

        runs = RunService(repo=_FakeRunRepo())
        controller = RenderApiController(
            scripts=_FakeScriptService(),
            ideas=None,
            history=_FakeHistory(),
            project_service=_FakeProjectService(),
            task_manager=_FakeTaskManager(),
            config=AppConfig(),
            runs=runs,
            store=_NoiseStore(),
            profile_service=InvalidProfileService(_profile(0)),
        )
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        result = await controller.start_render(
            request=_Request({"project_id": "p1", "idea_index": "0"})
        )
        assert "Project settings are invalid" in str(result)
        assert _PipelineSpy.instances == []
        assert await runs.list_by_project("p1") == []
