"""Page tests for the reorganized Global Settings and the canonical Topics surface."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from lexigram.sql.providers.database_service import DatabaseService

from shorts_creator.controllers.settings import SettingsController
from shorts_creator.controllers.topics import TopicsController
from shorts_creator.services.core import AppConfig
from shorts_creator.services.settings_store import SettingsStore
from shorts_creator.services.topic_profile_service import TopicProfileService
from shorts_creator.topics.registry import TopicRegistry

REPO_ROOT = Path(__file__).resolve().parent.parent


class FakeFormRequest:
    def __init__(self, form_data: dict[str, str]):
        self._form_data = form_data

    async def form(self):
        return self._form_data


async def body_of(resp) -> str:
    return resp.body if hasattr(resp, "body") else str(resp)


async def _connected_service():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_url = f"sqlite:///{path}"
    alembic_url = f"sqlite+aiosqlite:///{path}"
    subprocess.run(
        ["alembic", "-c", "migrations/primary/alembic.ini", "upgrade", "head"],
        cwd=REPO_ROOT,
        env={**os.environ, "SHORTS_CREATOR_DATABASE_URL": alembic_url},
        check=True,
        capture_output=True,
    )
    service = DatabaseService(db_url)
    await service.connect()
    return service, path


@pytest.fixture
async def db_service():
    service, path = await _connected_service()
    yield service
    await service.disconnect()
    os.unlink(path)


@pytest.fixture
async def settings_controller(db_service):
    config = AppConfig.from_dict(
        {
            "reel_width": 1080,
            "reel_height": 1920,
            "default_duration": 30.0,
        }
    )
    yield SettingsController(config, SettingsStore(db_service))


@pytest.fixture
async def topics_controller(db_service):
    yield TopicsController(TopicProfileService(db_service))


@pytest.fixture
def skill_md():
    return REPO_ROOT / "data" / "skills" / "self_improvement" / "SKILL.md"


class TestGlobalSettingsPage:
    async def test_global_settings_prioritize_creative_defaults(self, settings_controller):
        body = await body_of(await settings_controller.view_settings())
        assert body.index("Creative Defaults") < body.index("LLM Providers")
        assert "Video Types" not in body.split("Creative Defaults", 1)[1].split("Advanced", 1)[0]

    async def test_global_settings_has_no_inline_topics_tab(self, settings_controller):
        body = await body_of(await settings_controller.view_settings())
        assert "tab=topics" not in body
        assert "Topics" not in body.split("Creative Defaults", 1)[1].split("Advanced", 1)[0]

    async def test_global_settings_keeps_creative_controls(self, settings_controller):
        body = await body_of(await settings_controller.view_settings())
        assert 'name="default_duration"' in body
        assert 'name="default_caption_style"' in body
        assert 'id="settings-creative-fields"' in body


class TestTopicsPage:
    async def test_topics_has_canonical_route_and_structured_editor(self, topics_controller):
        body = await body_of(await topics_controller.list_topics())
        assert "Topics" in body
        assert "/topics/self_improvement" in body

    async def test_list_shows_structured_columns(self, topics_controller):
        body = await body_of(await topics_controller.list_topics())
        for label in ("Structure", "Overrides", "Edit"):
            assert label in body

    async def test_editor_renders_structured_fields_readonly_and_editable(self, topics_controller):
        body = await body_of(await topics_controller.edit_topic(name="self_improvement"))
        assert 'name="topic_categories"' in body
        assert 'name="banned_phrases"' in body
        assert "Structure" in body
        assert "Prompt" in body

    async def test_editor_marks_duration_and_pacing_as_format_managed(self, topics_controller):
        body = await body_of(await topics_controller.edit_topic(name="self_improvement"))
        assert "Duration &amp; pacing" in body or "Duration & pacing" in body
        assert "FORMAT.md" in body
        assert 'name="duration_min"' not in body

    async def test_editor_reads_structured_overrides(self, topics_controller):
        await topics_controller.save(
            FakeFormRequest({"topic_categories": "Grit, Discipline"}),
            name="self_improvement",
        )
        profile = await topics_controller.profile_service.get("self_improvement")
        assert "Grit" in profile.topic_categories

    async def test_topic_save_does_not_rewrite_skill_prompt(self, topics_controller, skill_md):
        before = skill_md.read_text()
        await topics_controller.save(
            FakeFormRequest({"banned_phrases": "foo, bar"}),
            name="self_improvement",
        )
        assert skill_md.read_text() == before

    async def test_topic_save_persists_structured_overrides(self, topics_controller, db_service):
        await topics_controller.save(
            FakeFormRequest({"banned_phrases": "foo, bar"}),
            name="self_improvement",
        )
        profile = await TopicProfileService(db_service).get("self_improvement")
        assert "foo" in profile.banned_phrases

    async def test_topic_save_ignores_duration_form_fields(self, topics_controller):
        resp = await topics_controller.save(
            FakeFormRequest({"duration_min": "60", "duration_max": "30"}),
            name="self_improvement",
        )
        body = await body_of(resp)
        assert "saved" in body.lower()
        assert await topics_controller.profile_service.count_overrides("self_improvement") == 0


class TestGlobalSettingsDurationInput:
    async def test_default_duration_renders_number_input(self, settings_controller):
        body = await body_of(await settings_controller.view_settings())
        assert 'name="default_duration"' in body
        assert 'type="number"' in body


class TestGlobalSettingsProviderButtons:
    async def test_single_health_button(self, settings_controller):
        body = await body_of(await settings_controller.view_settings())
        assert "Test All Connections" in body
        assert "Refresh Provider Health" not in body


class TestGlobalSettingsVideoSizeChip:
    async def test_video_size_row_shows_global_default_chip(self, settings_controller):
        body = await body_of(await settings_controller.view_settings())
        assert "1080x1920" in body
        assert 'ml-2">Global Default' in body


class _NoPromptsTopic:
    """Minimal registry topic carrying no prompt templates."""

    def __init__(self):
        self.name = "empty_topic"
        self.label = "Empty Topic"
        self.description = "A topic with no prompt templates."
        self.structure_sections = ["hook"]
        self.topic_categories = []
        self.banned_phrases = []
        self.idea_prompt = ""
        self.script_prompt = ""


class TestTopicListOverrideChip:
    async def test_overrides_chip_muted_when_zero(self, topics_controller):
        body = await body_of(await topics_controller.list_topics())
        assert "Overrides: 0" in body
        assert "bg-warning/40" not in body


class TestTopicEditorPacingChips:
    async def test_editor_shows_chips_for_strategy_topic(self, topics_controller):
        body = await body_of(await topics_controller.edit_topic(name="self_improvement"))
        assert "Duration:" in body
        assert "wps" in body
        assert "via" in body


class TestTopicEditorPromptBlocks:
    async def test_editor_renders_labeled_prompt_blocks(self, topics_controller):
        body = await body_of(await topics_controller.edit_topic(name="self_improvement"))
        assert "Idea prompt" in body
        assert "Script prompt" in body

    async def test_editor_without_prompts_does_not_500(self, topics_controller):
        registry = TopicRegistry()
        registry.register(_NoPromptsTopic())
        controller = TopicsController(TopicProfileService(topic_registry=registry))
        resp = await controller.edit_topic(name="empty_topic")
        body = await body_of(resp)
        assert "Idea prompt" not in body
