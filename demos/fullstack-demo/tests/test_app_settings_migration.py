import os
import subprocess
import tempfile

import pytest
from lexigram.sql.providers.database_service import DatabaseService

from shorts_creator.repositories.project_repository import ProjectRepository
from shorts_creator.services.core import AppConfig
from shorts_creator.services.project_service import ProjectService

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
async def migrated_db():
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
    yield service
    await service.disconnect()
    os.unlink(path)


class TestAppSettingsUpdatedAtColumn:
    async def test_insert_with_updated_at_succeeds(self, migrated_db):
        result = await migrated_db.execute(
            "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            ("default_duration", "42"),
        )
        assert result.success, result.error_message


class TestSchema010DropsCtaColumns:
    async def test_head_upgrade_removes_cta_columns(self):
        import sqlite3

        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        subprocess.run(
            ["alembic", "-c", "migrations/primary/alembic.ini", "upgrade", "head"],
            cwd=REPO_ROOT,
            env={**os.environ, "SHORTS_CREATOR_DATABASE_URL": f"sqlite+aiosqlite:///{path}"},
            check=True,
            capture_output=True,
        )
        conn = sqlite3.connect(path)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(projects)")}
        conn.close()
        os.unlink(path)
        assert "cta_enabled" not in cols
        assert "cta_lead_in" not in cols
        assert "cta_display" not in cols


def _upgrade(path: str, target: str) -> None:
    subprocess.run(
        ["alembic", "-c", "migrations/primary/alembic.ini", "upgrade", target],
        cwd=REPO_ROOT,
        env={**os.environ, "SHORTS_CREATOR_DATABASE_URL": f"sqlite+aiosqlite:///{path}"},
        check=True,
        capture_output=True,
    )


class TestSchema012BootSafety:
    """Task 10 step 2: fresh upgrade reaches head and the app boots."""

    async def test_fresh_upgrade_head_is_schema_013(self, monkeypatch):
        import sqlite3

        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        _upgrade(path, "head")

        conn = sqlite3.connect(path)
        row = conn.execute("SELECT version_num FROM alembic_primary").fetchone()
        conn.close()
        assert row == ("schema_013",)

        monkeypatch.setenv("LEX_SQL__BACKEND__URL", f"sqlite:///{path}")
        from lexigram.app import Application

        from shorts_creator.main import RootModule
        from shorts_creator.services.project_profile_service import ProjectProfileService
        from shorts_creator.services.project_service import ProjectService

        async with Application.boot(name="shorts-creator", modules=[RootModule.configure()]) as app:
            profile_service = await app.container.resolve(ProjectProfileService)
            projects = await app.container.resolve(ProjectService)
            assert profile_service is not None
            assert projects is not None
        os.unlink(path)

    async def test_legacy_overrides_db_upgrades_and_resolves_invalid_values(self):
        """Legacy rows (cta columns, invalid duration text) migrate to head and
        resolve through ProjectProfileService without crashing on garbage."""
        import json
        import sqlite3

        from shorts_creator.services.project_profile_service import (
            ProfileSource,
            ProjectProfileService,
        )
        from shorts_creator.services.settings_store import SettingsStore

        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        _upgrade(path, "schema_009")

        conn = sqlite3.connect(path)
        conn.execute(
            """INSERT INTO projects (id, topic, focus, title, created_at, updated_at,
               default_duration, cta_enabled, cta_lead_in, cta_display, format, caption_style)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "legacy-good",
                "self_improvement",
                "",
                "",
                "2026-08-01T00:00:00",
                "2026-08-01T00:00:00",
                42,
                1,
                5.0,
                3.0,
                "narration",
                "plain",
            ),
        )
        conn.execute(
            """INSERT INTO projects (id, topic, focus, title, created_at, updated_at,
               default_duration, cta_enabled, format, caption_style)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "legacy-bad",
                "retired-topic",
                "",
                "",
                "2026-08-01T00:00:00",
                "2026-08-01T00:00:00",
                "not-an-int",
                None,
                "narration",
                "garbage",
            ),
        )
        conn.execute(
            "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            ("default_duration", "not-a-float"),
        )
        conn.commit()
        conn.close()

        _upgrade(path, "head")

        service = DatabaseService(f"sqlite:///{path}")
        await service.connect()
        try:
            config = AppConfig.from_dict(
                {
                    "reel_width": 1080,
                    "reel_height": 1920,
                    "default_duration": 30.0,
                }
            )
            store = SettingsStore(service)
            projects = ProjectService(ProjectRepository(service))
            profile_service = ProjectProfileService(config, store)

            good = await profile_service.resolve(await projects.get("legacy-good"))
            assert good.duration_seconds.value == 42.0
            assert good.duration_seconds.source is ProfileSource.PROJECT
            assert json.loads((await projects.get("legacy-good")).profile_overrides_json) == {
                "duration_seconds": 42,
                "format_name": "narration",
                "caption_style": "plain",
            }

            bad = await profile_service.resolve(await projects.get("legacy-bad"))
            assert bad.duration_seconds.value == 30.0
            assert bad.duration_seconds.source is ProfileSource.BUILT_IN
        finally:
            await service.disconnect()
        os.unlink(path)
