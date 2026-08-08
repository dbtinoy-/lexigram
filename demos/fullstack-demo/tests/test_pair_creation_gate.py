import json

import pytest

from shorts_creator.contracts.matcher import TopicSide
from shorts_creator.controllers.projects import ProjectsController
from shorts_creator.formats import registry as format_registry
from shorts_creator.formats.base import FormatDefinition
from shorts_creator.models.project import Project
from shorts_creator.models.project_profile import ProfileSource
from shorts_creator.services.core import AppConfig
from shorts_creator.services.project_profile_service import (
    ProjectProfileService,
    compatible_formats,
    pair_block_message,
)
from shorts_creator.topics import registry as topics_registry


def fake_listicle() -> FormatDefinition:
    return FormatDefinition(
        name="listicle",
        label="Listicle",
        description="Multi-item listicle",
        caption_styles=["highlight"],
        default_caption_style="highlight",
        requires={
            "script": ["message_lines", "closing"],
            "voice": ["tts_story"],
            "pipeline": ["tts_story", "word_timing", "captions"],
        },
    )


class FakeTopic:
    """Minimal topic contract stand-in: default_format + contract side."""

    def __init__(self, name: str, default_format: str, script: set[str]):
        self.name = name
        self.default_format = default_format
        self._script = script

    def to_contract_side(self) -> TopicSide:
        return TopicSide(
            script=frozenset(self._script), voice={"tts_story"}, objectives=frozenset()
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


class TestCascadeResolve:
    async def test_override_wins_over_topic_default(self, profile_service):
        result = await profile_service.resolve(
            project=Project(
                topic="stoic",
                profile_overrides_json='{"format_name": "listicle"}',
            ),
            global_values={},
        )
        assert result.format_name.value == "listicle"
        assert result.format_name.source is ProfileSource.PROJECT

    async def test_topic_default_used_when_registered(self, profile_service):
        result = await profile_service.resolve(
            project=Project(topic="stoic"),
            global_values={},
        )
        assert result.format_name.value == "narrated"
        assert result.format_name.source is ProfileSource.BUILT_IN

    async def test_first_compatible_format_when_default_unregistered(
        self, profile_service, listicle_registered, monkeypatch
    ):
        listicle_registered()
        monkeypatch.setattr(
            topics_registry,
            "_topics",
            {
                "newskill": FakeTopic("newskill", "no-such-default", {"message_lines", "closing"}),
            },
        )
        result = await profile_service.resolve(
            project=Project(topic="newskill"),
            global_values={},
        )
        assert result.format_name.value == "listicle"
        assert result.format_name.source is ProfileSource.BUILT_IN

    async def test_incompatible_formats_skipped_in_cascade(
        self, profile_service, listicle_registered, monkeypatch
    ):
        listicle_registered()
        monkeypatch.setattr(
            topics_registry,
            "_topics",
            {
                "stoic": FakeTopic("stoic", "no-such-default", {"hook", "problem"}),
            },
        )
        result = await profile_service.resolve(
            project=Project(topic="stoic"),
            global_values={},
        )
        assert result.format_name.value == "narrated"

    async def test_unknown_topic_falls_back_to_legacy(self, profile_service, listicle_registered):
        listicle_registered()
        result = await profile_service.resolve(
            project=Project(topic="no_such_topic"),
            global_values={},
        )
        assert result.format_name.value == "narrated"
        assert result.format_name.source is ProfileSource.BUILT_IN


class TestCompatibleFormats:
    def test_all_registered_topics_compatible_with_narrated(self):
        for topic in topics_registry.available:
            assert compatible_formats(topic.name) == ["narrated", "topn", "myth", "steps"]

    def test_no_topic_means_all_formats(self):
        assert compatible_formats(None) == ["narrated", "topn", "myth", "steps"]

    def test_incompatible_topic_excludes_listicle(self, listicle_registered):
        listicle_registered()
        assert compatible_formats("stoic") == ["narrated", "topn", "myth", "steps"]

    def test_compatible_topic_includes_listicle(self, monkeypatch):
        monkeypatch.setattr(
            topics_registry,
            "_topics",
            {
                "listicle_guy": FakeTopic("listicle_guy", None, {"message_lines", "closing"}),
            },
        )
        merged = dict(format_registry._formats)
        merged["listicle"] = fake_listicle()
        monkeypatch.setattr(format_registry, "_formats", merged)
        assert compatible_formats("listicle_guy") == ["listicle"]


class TestPairBlockMessage:
    def test_valid_pair_no_message(self):
        assert pair_block_message("stoic", "narrated") is None

    def test_unknown_sides_no_message(self):
        assert pair_block_message(None, None) is None
        assert pair_block_message("stoic", "no-such-format") is None
        assert pair_block_message("no_such_topic", "narrated") is None

    def test_incompatible_pair_reports_error(self, listicle_registered):
        listicle_registered()
        message = pair_block_message("stoic", "listicle")
        assert message is not None
        assert message.startswith("REQ_SCRIPT")


class FakeProjectRepo:
    def __init__(self):
        self.store: dict[str, Project] = {}

    async def create(self, project):
        self.store[project.id] = project
        return project

    async def get(self, project_id):
        return self.store.get(project_id)


class FakeProjectService:
    def __init__(self, repo):
        self.repo = repo

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

    async def form(self):
        return self._form_data

    async def json(self):
        raise TypeError("no json body")


class TestCreateGate:
    async def test_incompatible_pair_returns_blocked_fragment(self, listicle_registered):
        listicle_registered()
        controller = ProjectsController(projects=FakeProjectService(FakeProjectRepo()))
        response = await controller.upsert_project(
            request=FakeFormRequest(
                {"title": "T", "topic": "stoic", "format": "listicle", "caption_style": "plain"}
            )
        )
        body = response.body if hasattr(response, "body") else str(response)
        assert "REQ_SCRIPT" in body
        assert not controller.projects.repo.store

    async def test_incompatible_pair_has_no_redirect(self, listicle_registered):
        listicle_registered()
        controller = ProjectsController(projects=FakeProjectService(FakeProjectRepo()))
        response = await controller.upsert_project(
            request=FakeFormRequest({"topic": "stoic", "format": "listicle"})
        )
        headers = getattr(response, "headers", {})
        assert "HX-Redirect" not in headers

    async def test_valid_pair_creates_project(self):
        controller = ProjectsController(projects=FakeProjectService(FakeProjectRepo()))
        response = await controller.upsert_project(
            request=FakeFormRequest(
                {"title": "T", "topic": "stoic", "format": "narrated", "caption_style": "plain"}
            )
        )
        assert getattr(response, "headers", {}).get("HX-Redirect")
        assert len(controller.projects.repo.store) == 1
