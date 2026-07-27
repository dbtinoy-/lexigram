import os
import subprocess
import tempfile
import uuid

import pytest
from lexigram.sql.providers.database_service import DatabaseService

from shorts_creator.services.settings_store import SettingsStore

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
async def store():
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
    yield SettingsStore(service)
    await service.disconnect()
    os.unlink(path)


class TestSettingsStore:
    async def test_save_then_get_overrides_roundtrips(self, store):
        await store.save({"default_duration": "42"})
        overrides = await store.get_overrides()
        assert overrides["default_duration"] == "42"

    async def test_save_ignores_keys_not_on_the_allow_list(self, store):
        await store.save({"evil_key": "drop table projects"})
        overrides = await store.get_overrides()
        assert "evil_key" not in overrides

    async def test_save_overwrites_existing_value(self, store):
        await store.save({"default_duration": "45"})
        await store.save({"default_duration": "30"})
        overrides = await store.get_overrides()
        assert overrides["default_duration"] == "30"

    async def test_get_json_defaults_when_missing_or_garbage(self, store):
        assert await store.get_json("composer_presets") is None
        await store._db.execute(
            "INSERT OR REPLACE INTO app_settings (key, value, updated_at) "
            "VALUES ('composer_presets', 'not-json', datetime('now'))"
        )
        assert await store.get_json("composer_presets") is None

    async def test_set_json_roundtrips(self, store):
        payload = [{"name": "A", "payload": {"format_name": "narrated"}}]
        await store.set_json("composer_presets", payload)
        assert await store.get_json("composer_presets") == payload

    async def test_get_overrides_empty_when_nothing_saved(self, store):
        assert await store.get_overrides() == {}

    async def test_global_values_only_include_allowed_keys(self, store):
        await store.save(
            {
                "default_duration": "42",
                "default_caption_style": "plain",
                "asset_default_music_id": "42",
            }
        )
        await store._db.execute(
            "INSERT OR REPLACE INTO app_settings (key, value, updated_at) "
            "VALUES ('stray_key', 'x', datetime('now'))"
        )
        values = await store.get_global_values()
        assert values == {
            "default_duration": "42",
            "default_caption_style": "plain",
            "asset_default_music_id": "42",
        }

    async def test_save_global_values_roundtrips(self, store):
        rejected = await store.save_global_values(
            {
                "default_duration": "45",
                "default_caption_style": "plain",
            }
        )
        assert rejected == {}
        values = await store.get_global_values()
        assert values["default_duration"] == "45"
        assert values["default_caption_style"] == "plain"

    async def test_save_global_values_rejects_unknown_fields(self, store):
        rejected = await store.save_global_values({"csrf_token": "abc"})
        assert "csrf_token" in rejected

    async def test_save_global_values_rejects_invalid_values(self, store):
        rejected = await store.save_global_values(
            {
                "default_duration": "-1",
                "default_caption_style": "bogus",
            }
        )
        assert rejected["default_duration"]
        assert rejected["default_caption_style"]
        assert await store.get_global_values() == {}

    async def test_save_global_values_writes_nothing_when_all_invalid(self, store):
        rejected = await store.save_global_values({"default_duration": "-1"})
        assert rejected
        assert await store.get_global_values() == {}

    async def test_save_validates_new_keys_with_old_api(self, store):
        rejected = await store.save({"default_duration": "-1"})
        assert "default_duration" in rejected
        assert await store.get_global_values() == {}

    async def test_save_rejects_bools_for_timing_fields(self, store):
        rejected = await store.save_global_values(
            {
                "default_duration": True,
                "default_caption_style": False,
            }
        )
        assert rejected["default_duration"]
        assert rejected["default_caption_style"]
        assert await store.get_global_values() == {}

    async def test_credentials_save_and_roundtrip(self, store):
        rejected = await store.save_global_values(
            {
                "pexels_api_key": "px-123",
                "pixabay_api_key": "pb-456",
            }
        )
        assert rejected == {}
        assert await store.get_credentials() == {
            "pexels_api_key": "px-123",
            "pixabay_api_key": "pb-456",
        }
        assert await store.get_global_values() == {}

    async def test_credentials_are_stripped_and_cleared_by_empty_value(self, store):
        await store.save_global_values({"pexels_api_key": "  px-123  "})
        assert await store.get_credentials() == {"pexels_api_key": "px-123"}
        await store.save_global_values({"pexels_api_key": ""})
        assert await store.get_credentials() == {}

    async def test_get_credentials_never_leaks_other_settings(self, store):
        await store.save({"default_duration": "42", "pexels_api_key": "px-123"})
        assert await store.get_credentials() == {"pexels_api_key": "px-123"}

    async def test_configured_providers_from_stored_keys(self, store):
        await store.save_global_values({"pexels_api_key": "px-123", "pixabay_api_key": "pb-456"})
        assert await store.configured_providers() == ["pexels", "pixabay"]

    async def test_configured_providers_from_env_fallback(self, store, monkeypatch):
        monkeypatch.setenv("PEXELS_API_KEY", "px-env")
        monkeypatch.delenv("PIXABAY_API_KEY", raising=False)
        assert await store.configured_providers() == ["pexels"]

    async def test_configured_providers_empty_without_keys(self, store, monkeypatch):
        monkeypatch.delenv("PEXELS_API_KEY", raising=False)
        monkeypatch.delenv("PIXABAY_API_KEY", raising=False)
        assert await store.configured_providers() == []


class TestEmptyValuePurgesOnSave:
    async def test_save_empty_global_value_deletes_row(self, store):
        await store.save({"default_caption_style": "list"})
        await store.save({"default_caption_style": ""})
        assert "default_caption_style" not in await store.get_overrides()

    async def test_save_empty_asset_id_deletes_row(self, store):
        await store.save({"asset_default_music_id": "42"})
        await store.save({"asset_default_music_id": ""})
        assert "asset_default_music_id" not in await store.get_overrides()

    async def test_save_empty_value_keeps_sibling_rows(self, store):
        await store.save({"default_caption_style": "list", "default_duration": "45"})
        await store.save({"default_caption_style": ""})
        overrides = await store.get_overrides()
        assert "default_caption_style" not in overrides
        assert overrides["default_duration"] == "45"

    async def test_save_global_values_empty_value_purges_row(self, store):
        await store.save_global_values({"default_caption_style": "plain"})
        rejected = await store.save_global_values({"default_caption_style": ""})
        assert rejected == {}
        assert "default_caption_style" not in await store.get_overrides()

    async def test_save_non_empty_value_still_stored(self, store):
        await store.save({"default_caption_style": "list"})
        await store.save({"default_caption_style": ""})
        await store.save({"default_caption_style": "plain"})
        assert (await store.get_overrides())["default_caption_style"] == "plain"


class TestPerKeyValidation:
    async def test_caption_style_rejects_unknown_value(self, store):
        rejected = await store.save_global_values({"default_caption_style": "weird"})
        assert "default_caption_style" in rejected
        assert await store.get_global_values() == {}

    async def test_caption_style_accepts_empty_value(self, store):
        rejected = await store.save_global_values({"default_caption_style": ""})
        assert rejected == {}
        assert "default_caption_style" not in await store.get_overrides()

    async def test_asset_id_rejects_non_numeric_value(self, store):
        rejected = await store.save_global_values({"asset_default_music_id": "abc"})
        assert "asset_default_music_id" in rejected

    async def test_asset_id_accepts_empty_value(self, store):
        rejected = await store.save_global_values({"asset_default_font_id": ""})
        assert rejected == {}
        assert "asset_default_font_id" not in await store.get_overrides()

    async def test_asset_id_accepts_numeric_value(self, store):
        rejected = await store.save_global_values({"asset_default_watermark_id": "42"})
        assert rejected == {}
        assert (await store.get_overrides())["asset_default_watermark_id"] == "42"

    async def test_asset_id_accepts_uuid_value(self, store):
        asset_id = "567acf40-e583-4ad8-8818-d356934ea736"
        rejected = await store.save_global_values(
            {
                "asset_default_music_id": asset_id,
                "asset_default_outro_clip_id": str(uuid.uuid4()),
            }
        )
        assert rejected == {}
        assert (await store.get_global_values()).get("asset_default_music_id") == asset_id

    async def test_asset_id_rejects_bool(self, store):
        rejected = await store.save_global_values({"asset_default_bg_clip_id": True})
        assert "asset_default_bg_clip_id" in rejected

    async def test_all_five_asset_keys_validated(self, store):
        rejected = await store.save_global_values(
            {
                "asset_default_music_id": "abc",
                "asset_default_font_id": "abc",
                "asset_default_watermark_id": "abc",
                "asset_default_bg_clip_id": "abc",
                "asset_default_outro_clip_id": "abc",
            }
        )
        assert set(rejected) == {
            "asset_default_music_id",
            "asset_default_font_id",
            "asset_default_watermark_id",
            "asset_default_bg_clip_id",
            "asset_default_outro_clip_id",
        }

    async def test_duration_still_rejects_non_numeric(self, store):
        rejected = await store.save_global_values({"default_duration": "abc"})
        assert "default_duration" in rejected
        assert await store.get_global_values() == {}

    async def test_all_supported_caption_styles_accepted(self, store):
        for style in ("highlight", "plain", "list"):
            rejected = await store.save_global_values({"default_caption_style": style})
            assert rejected == {}
            assert (await store.get_overrides())["default_caption_style"] == style

    async def test_save_global_values_batch_persists_nothing_when_one_invalid(self, store):
        rejected = await store.save_global_values(
            {
                "default_caption_style": "list",
                "default_duration": "45",
                "asset_default_music_id": "abc",
            }
        )
        assert "asset_default_music_id" in rejected
        assert await store.get_global_values() == {}
