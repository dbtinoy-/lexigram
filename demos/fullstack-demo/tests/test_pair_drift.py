import json
from typing import ClassVar

import pytest

from shorts_creator.contracts.issues import ContractIssue, Severity
from shorts_creator.controllers.api.render_api import RenderApiController
from shorts_creator.formats import registry as format_registry
from shorts_creator.formats.base import FormatDefinition
from shorts_creator.models.project import Project
from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProfileSource,
    ResolvedSetting,
)
from shorts_creator.services.core import AppConfig
from shorts_creator.services.project_profile_service import ProjectProfileService
from shorts_creator.services.run_service import RunService


def fake_listicle() -> FormatDefinition:
    return FormatDefinition(
        name="listicle",
        label="Listicle",
        description="Multi-item listicle",
        caption_styles=["highlight", "plain"],
        default_caption_style="highlight",
        requires={
            "script": ["message_lines", "closing"],
            "voice": ["tts_story"],
            "pipeline": ["tts_story", "word_timing", "captions"],
        },
    )


@pytest.fixture
def listicle_registered(monkeypatch):
    def _patch(formats: dict[str, FormatDefinition] | None = None):
        merged = dict(format_registry._formats)
        merged["listicle"] = fake_listicle()
        monkeypatch.setattr(format_registry, "_formats", merged)

    return _patch


@pytest.fixture
def profile_service():
    return ProjectProfileService(
        config=AppConfig.from_dict(
            {"reel_width": 1080, "reel_height": 1920, "default_duration": 30.0}
        ),
    )


class TestValidatePairForProject:
    async def test_valid_pair_has_no_issues(self, profile_service):
        project = Project(topic="stoic")
        assert await profile_service.validate_pair_for_project(project) == []

    async def test_drifted_format_reports_req_script(self, profile_service, listicle_registered):
        listicle_registered()
        project = Project(
            topic="stoic",
            profile_overrides_json='{"format_name": "listicle"}',
        )
        issues = await profile_service.validate_pair_for_project(project)
        assert any(i.code == "REQ_SCRIPT" for i in issues)
        assert all(i.severity is Severity.ERROR for i in issues)

    async def test_unsupported_caption_style_reports_req_style(self, profile_service):
        project = Project(
            topic="stoic",
            profile_overrides_json='{"caption_style": "fancy"}',
        )
        issues = await profile_service.validate_pair_for_project(project)
        assert any(i.code == "REQ_STYLE" for i in issues)

    async def test_missing_required_asset_reports_req_asset(self, profile_service, monkeypatch):
        asset_requiring = FormatDefinition(
            name="cinematic",
            label="Cinematic",
            description="",
            caption_styles=["highlight"],
            default_caption_style="highlight",
            requires={"script": ["hook"], "voice": ["tts_story"], "assets": ["music"]},
        )
        merged = dict(format_registry._formats)
        merged["cinematic"] = asset_requiring
        monkeypatch.setattr(format_registry, "_formats", merged)
        project = Project(
            topic="stoic",
            profile_overrides_json='{"format_name": "cinematic"}',
        )
        issues = await profile_service.validate_pair_for_project(project)
        assert any(i.code == "REQ_ASSET" for i in issues)

    async def test_selected_asset_satisfies_req_asset(self, profile_service, monkeypatch):
        asset_requiring = FormatDefinition(
            name="cinematic",
            label="Cinematic",
            description="",
            caption_styles=["highlight"],
            default_caption_style="highlight",
            requires={"script": ["hook"], "voice": ["tts_story"], "assets": ["music"]},
        )
        merged = dict(format_registry._formats)
        merged["cinematic"] = asset_requiring
        monkeypatch.setattr(format_registry, "_formats", merged)
        project = Project(
            topic="stoic",
            profile_overrides_json=('{"format_name": "cinematic", "asset_music_id": "music-1"}'),
        )
        issues = await profile_service.validate_pair_for_project(project)
        assert not any(i.code == "REQ_ASSET" for i in issues)

    async def test_unloaded_resolved_format_reports_format_not_loaded(self, profile_service):
        project = Project(
            topic="stoic",
            profile_overrides_json='{"format_name": "no-such-format"}',
        )
        issues = await profile_service.validate_pair_for_project(project)
        assert [i.code for i in issues] == ["FORMAT_NOT_LOADED"]

    async def test_unknown_topic_has_no_issues(self, profile_service):
        project = Project(topic="no_such_topic")
        assert await profile_service.validate_pair_for_project(project) == []


class _FakeProject:
    id = "p1"
    topic = "self_improvement"
    idea_json = "{}"
    profile_overrides_json = None


class _FakeProjectService:
    async def get(self, project_id):
        return _FakeProject()


class _FakeProfileService:
    def __init__(self, pair_issues=None):
        self._pair_issues = pair_issues or []

    async def resolve(self, project):
        return None

    @staticmethod
    def validate(profile):
        return {}

    async def validate_pair_for_project(self, project):
        return self._pair_issues


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


class _FakeTaskManager:
    def track_named(self, name, coro):
        coro.close()
        return type("FakeTask", (), {"done": lambda self: True})()


def _make_controller(profile_service):
    return RenderApiController(
        scripts=None,
        ideas=None,
        history=None,
        project_service=_FakeProjectService(),
        task_manager=_FakeTaskManager(),
        config=AppConfig.from_dict({"default_duration": 30.0}),
        runs=RunService(_FakeRunRepo()),
        profile_service=profile_service,
    )


def _issue(code: str, message: str) -> ContractIssue:
    return ContractIssue(Severity.ERROR, code, message)


def _form_request(data: dict):
    class _R:
        headers: ClassVar[dict] = {"content-type": "application/x-www-form-urlencoded"}

        async def form(self):
            return data

    return _R()


class TestRenderGateBlocksDrift:
    async def test_error_issue_blocks_render(self):
        controller = _make_controller(_FakeProfileService([_issue("REQ_SCRIPT", "hook missing")]))
        response = await controller.start_render(request=_form_request({"project_id": "p1"}))
        body = response.body if hasattr(response, "body") else str(response)
        assert "Topic/format contract violation" in body
        assert "REQ_SCRIPT" in body

    async def test_error_issue_creates_no_run(self):
        controller = _make_controller(
            _FakeProfileService([_issue("REQ_STYLE", "style unsupported")])
        )
        await controller.start_render(request=_form_request({"project_id": "p1"}))
        assert not controller.runs.repo.store

    async def test_warn_issue_does_not_block(self):
        warn = ContractIssue(Severity.WARN, "OBJ_NOT_SUPPORTED", "objective not producible")
        controller = _make_controller(_FakeProfileService([warn]))
        response = await controller.start_render(
            request=_form_request({"project_id": "p1", "idea_index": "0"})
        )
        body = response.body if hasattr(response, "body") else str(response)
        assert "contract violation" not in body


class TestRunSnapshotPairIssues:
    async def test_create_with_profile_starts_without_pair_issues(self):
        effective = EffectiveProjectProfile(
            duration_seconds=ResolvedSetting(45, ProfileSource.BUILT_IN, False),
            caption_style=ResolvedSetting("highlight", ProfileSource.BUILT_IN, False),
            format_name=ResolvedSetting("narrated", ProfileSource.BUILT_IN, False),
            topic=ResolvedSetting("stoic", ProfileSource.BUILT_IN, False),
            reel_width=ResolvedSetting(1080, ProfileSource.BUILT_IN, False),
            reel_height=ResolvedSetting(1920, ProfileSource.BUILT_IN, False),
        )
        runs = RunService(_FakeRunRepo())
        run = await runs.create_with_profile("p1", "T", effective)
        assert "pair_issues" not in json.loads(run.settings_snapshot_json)

    async def test_update_profile_snapshot_records_pair_issues(self):
        runs = RunService(_FakeRunRepo())
        run = await runs.create("p1", "T")
        await runs.update_profile_snapshot(
            run.id,
            {"pair_issues": [{"code": "OBJ_NOT_SUPPORTED", "message": "m"}]},
        )
        snapshot = await runs.get_snapshot(run.id)
        assert snapshot["pair_issues"] == [{"code": "OBJ_NOT_SUPPORTED", "message": "m"}]
