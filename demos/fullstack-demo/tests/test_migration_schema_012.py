import importlib.util
import json
import os
import sqlite3
import subprocess
import tempfile
from types import SimpleNamespace

import pytest
from lexigram.sql.providers.database_service import DatabaseService

from shorts_creator.models.project import Project
from shorts_creator.models.run import Run

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _load_migration(name: str):
    path = os.path.join(REPO_ROOT, "migrations", "primary", "versions", f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _alembic_url(path: str) -> str:
    return f"sqlite+aiosqlite:///{path}"


@pytest.fixture
async def migrated_db():
    """DB migrated to head, seeded with legacy-format project rows before schema_012."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    url = _alembic_url(path)
    subprocess.run(
        ["alembic", "-c", "migrations/primary/alembic.ini", "upgrade", "schema_011"],
        cwd=REPO_ROOT,
        env={**os.environ, "SHORTS_CREATOR_DATABASE_URL": url},
        check=True,
        capture_output=True,
    )
    conn = sqlite3.connect(path)
    conn.execute(
        """INSERT INTO projects (id, topic, format, caption_style, default_duration, asset_music_id, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "legacy-project",
            "self_improvement",
            "narration",
            "plain",
            42,
            "music-1",
            "2026-08-01T00:00:00",
            "2026-08-01T00:00:00",
        ),
    )
    conn.execute(
        """INSERT INTO projects (id, topic, format, caption_style, default_duration, asset_music_id, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "legacy-garbage",
            "psychology",
            "narration",
            "garbage",
            "not-an-int",
            "",
            "2026-08-01T00:00:00",
            "2026-08-01T00:00:00",
        ),
    )
    conn.commit()
    conn.close()
    subprocess.run(
        ["alembic", "-c", "migrations/primary/alembic.ini", "upgrade", "head"],
        cwd=REPO_ROOT,
        env={**os.environ, "SHORTS_CREATOR_DATABASE_URL": url},
        check=True,
        capture_output=True,
    )
    service = DatabaseService(f"sqlite:///{path}")
    await service.connect()
    yield service
    await service.disconnect()
    os.unlink(path)


class TestSchema012AddsProfileStorage:
    async def test_adds_profile_storage_and_backfills_legacy_values(self, migrated_db):
        res = await migrated_db.execute_query(
            "SELECT profile_overrides_json FROM projects WHERE id = 'legacy-project'"
        )
        row = res.rows[0]
        assert json.loads(row["profile_overrides_json"]) == {
            "duration_seconds": 42,
            "caption_style": "plain",
            "format_name": "narration",
            "asset_music_id": "music-1",
        }

    async def test_creates_topic_profiles_and_run_snapshot_columns(self, migrated_db):
        tables = (
            await migrated_db.execute_query("SELECT name FROM sqlite_master WHERE type = 'table'")
        ).rows
        assert "topic_profiles" in {r["name"] for r in tables}
        cols = (await migrated_db.execute_query("PRAGMA table_info(runs)")).rows
        assert "settings_snapshot_json" in {r["name"] for r in cols}

    async def test_invalid_legacy_values_are_omitted(self, migrated_db):
        res = await migrated_db.execute_query(
            "SELECT profile_overrides_json FROM projects WHERE id = 'legacy-garbage'"
        )
        row = res.rows[0]
        assert json.loads(row["profile_overrides_json"]) == {
            "format_name": "narration",
            "caption_style": "garbage",
        }

    async def test_non_override_columns_survive_migration(self, migrated_db):
        res = await migrated_db.execute_query(
            "SELECT id, topic, focus, title, idea_json FROM projects WHERE id = 'legacy-project'"
        )
        row = res.rows[0]
        assert row["id"] == "legacy-project"
        assert row["topic"] == "self_improvement"

    async def test_legacy_columns_are_dropped(self, migrated_db):
        cols = (await migrated_db.execute_query("PRAGMA table_info(projects)")).rows
        names = {r["name"] for r in cols}
        assert (
            not {
                "default_duration",
                "format",
                "caption_style",
                "asset_music_id",
                "asset_font_id",
                "asset_watermark_id",
                "asset_bg_clip_id",
                "asset_outro_clip_id",
            }
            & names
        )

    def test_backfill_coerces_string_duration_to_int(self):
        migration = _load_migration("schema_012_project_profiles")
        row = SimpleNamespace(
            default_duration="60",
            format="narration",
            caption_style="plain",
            asset_music_id="music-1",
            asset_font_id=None,
            asset_watermark_id=None,
            asset_bg_clip_id=None,
            asset_outro_clip_id=None,
        )
        assert migration._profile_values(row) == {
            "duration_seconds": 60,
            "format_name": "narration",
            "caption_style": "plain",
            "asset_music_id": "music-1",
        }
        assert isinstance(migration._profile_values(row)["duration_seconds"], int)


class TestSchema012Downgrade:
    async def test_downgrade_restores_legacy_columns(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        url = _alembic_url(path)
        env = {**os.environ, "SHORTS_CREATOR_DATABASE_URL": url}
        subprocess.run(
            ["alembic", "-c", "migrations/primary/alembic.ini", "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
        )
        conn = sqlite3.connect(path)
        conn.executemany(
            """INSERT INTO projects (id, topic, profile_overrides_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (
                    "p1",
                    "t",
                    (
                        '{"duration_seconds": 42, "format_name": "narration", "caption_style": "plain",'
                        ' "asset_music_id": "music-1", "asset_font_id": "font-2",'
                        ' "asset_watermark_id": "wm-3", "asset_bg_clip_id": "bg-4",'
                        ' "asset_outro_clip_id": "outro-5"}'
                    ),
                    "2026-08-01T00:00:00",
                    "2026-08-01T00:00:00",
                ),
                (
                    "p2",
                    "t",
                    "not-json",
                    "2026-08-01T00:00:00",
                    "2026-08-01T00:00:00",
                ),
                (
                    "p3",
                    "t",
                    "{}",
                    "2026-08-01T00:00:00",
                    "2026-08-01T00:00:00",
                ),
            ],
        )
        conn.commit()
        conn.close()
        subprocess.run(
            ["alembic", "-c", "migrations/primary/alembic.ini", "downgrade", "schema_011"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
        )
        conn = sqlite3.connect(path)
        row = conn.execute(
            "SELECT default_duration, format, caption_style, asset_music_id, asset_font_id,"
            " asset_watermark_id, asset_bg_clip_id, asset_outro_clip_id"
            " FROM projects WHERE id = 'p1'"
        ).fetchone()
        corrupt = conn.execute(
            "SELECT default_duration, format, caption_style, asset_music_id"
            " FROM projects WHERE id = 'p2'"
        ).fetchone()
        empty = conn.execute(
            "SELECT default_duration, format, caption_style FROM projects WHERE id = 'p3'"
        ).fetchone()
        conn.close()
        os.unlink(path)
        assert row == (42, "narration", "plain", "music-1", "font-2", "wm-3", "bg-4", "outro-5")
        assert corrupt == (None, "narration", "highlight", None)
        assert empty == (None, "narration", "highlight")


class TestProfileJsonFields:
    def test_project_and_run_models_round_trip_json_fields(self):
        project = Project(
            topic="self_improvement", profile_overrides_json='{"duration_seconds": 45}'
        )
        run = Run(project_id=project.id, settings_snapshot_json='{"duration_seconds": 45}')
        assert json.loads(project.profile_overrides_json)["duration_seconds"] == 45
        assert json.loads(run.settings_snapshot_json)["duration_seconds"] == 45

    def test_string_duration_kwarg_is_coerced_to_int(self):
        project = Project(topic="self_improvement", default_duration="60")
        assert project.default_duration == 60
        assert isinstance(project.default_duration, int)
        assert json.loads(project.profile_overrides_json)["duration_seconds"] == 60

    def test_string_duration_in_json_is_coerced_to_int(self):
        project = Project(
            topic="self_improvement",
            profile_overrides_json='{"duration_seconds": "60"}',
        )
        assert project.default_duration == 60
        assert isinstance(project.default_duration, int)
