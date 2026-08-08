import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from lexigram.sql.providers.database_service import DatabaseService

from shorts_creator.models.project import Project
from shorts_creator.models.project_profile import ProfileSource
from shorts_creator.services.core import AppConfig
from shorts_creator.services.project_profile_service import ProjectProfileService
from shorts_creator.services.topic_profile_service import TopicProfileService

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _read_skill_md(name: str) -> str:
    md_path = Path(REPO_ROOT) / "data" / "skills" / name / "SKILL.md"
    return md_path.read_text(encoding="utf-8")


@pytest.fixture
async def topic_profiles():
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
    yield TopicProfileService(service)
    await service.disconnect()
    os.unlink(path)


class TestTopicProfileService:
    async def test_returns_builtin_profile_when_no_overrides(self, topic_profiles):
        profile = await topic_profiles.get("self_improvement")
        assert profile.name == "self_improvement"
        assert "hook" in profile.structure_sections
        assert "trust the process" in profile.banned_phrases

    async def test_topic_override_is_stored_separately_from_prompt_files(self, topic_profiles):
        await topic_profiles.save_overrides("self_improvement", {"topic_categories": ["New Angle"]})
        profile = await topic_profiles.get("self_improvement")
        assert "New Angle" in profile.topic_categories

    async def test_overrides_do_not_touch_skill_md_files(self, topic_profiles):
        before = _read_skill_md("self_improvement")
        await topic_profiles.save_overrides("self_improvement", {"banned_phrases": ["foo"]})
        after = _read_skill_md("self_improvement")
        assert before == after

    async def test_save_overrides_merges_with_existing(self, topic_profiles):
        await topic_profiles.save_overrides("self_improvement", {"topic_categories": ["A"]})
        await topic_profiles.save_overrides("self_improvement", {"topic_categories": ["A", "B"]})
        profile = await topic_profiles.get("self_improvement")
        assert profile.topic_categories == ["A", "B"]

    async def test_save_overrides_rejects_unknown_fields(self, topic_profiles):
        with pytest.raises(ValueError, match="unknown field"):
            await topic_profiles.save_overrides("self_improvement", {"caption_style": "plain"})

    async def test_save_overrides_rejects_duration_as_unknown_field(self, topic_profiles):
        with pytest.raises(ValueError, match="unknown field"):
            await topic_profiles.save_overrides("self_improvement", {"duration_range": [40, 50]})

    async def test_save_overrides_rejects_malformed_list(self, topic_profiles):
        with pytest.raises(ValueError):
            await topic_profiles.save_overrides(
                "self_improvement", {"banned_phrases": "not-a-list"}
            )

    async def test_save_overrides_rejects_unknown_topic(self, topic_profiles):
        with pytest.raises(ValueError, match="unknown topic"):
            await topic_profiles.save_overrides("no-such-topic", {"banned_phrases": ["x"]})

    async def test_get_unknown_topic_returns_none(self, topic_profiles):
        assert await topic_profiles.get("no-such-topic") is None

    async def test_list_returns_all_registry_topics(self, topic_profiles):
        profiles = await topic_profiles.list()
        names = [p.name for p in profiles]
        assert "self_improvement" in names
        assert "psychology" in names

    async def test_get_falls_back_to_builtin_when_overrides_json_is_corrupt(self, topic_profiles):
        await topic_profiles._db.execute(
            "INSERT OR REPLACE INTO topic_profiles "
            "(name, overrides_json, created_at, updated_at) VALUES (?, ?, datetime('now'), datetime('now'))",
            ("self_improvement", "{not-json"),
        )
        profile = await topic_profiles.get("self_improvement")
        assert "hook" in profile.structure_sections
        assert "trust the process" in profile.banned_phrases

    async def test_get_falls_back_to_builtin_when_override_list_is_malformed(self, topic_profiles):
        await topic_profiles._db.execute(
            "INSERT OR REPLACE INTO topic_profiles "
            "(name, overrides_json, created_at, updated_at) VALUES (?, ?, datetime('now'), datetime('now'))",
            ("self_improvement", '{"banned_phrases": "not-a-list"}'),
        )
        profile = await topic_profiles.get("self_improvement")
        assert "trust the process" in profile.banned_phrases

    async def test_resolve_still_works_when_overrides_json_is_corrupt(self, topic_profiles):
        await topic_profiles._db.execute(
            "INSERT OR REPLACE INTO topic_profiles "
            "(name, overrides_json, created_at, updated_at) VALUES (?, ?, datetime('now'), datetime('now'))",
            ("self_improvement", "{not-json"),
        )
        service = ProjectProfileService(
            config=AppConfig.from_dict(
                {
                    "reel_width": 1080,
                    "reel_height": 1920,
                    "default_duration": 30.0,
                }
            ),
        )
        result = await service.resolve(Project(topic="self_improvement"))
        assert result.duration_seconds.source is ProfileSource.FORMAT
