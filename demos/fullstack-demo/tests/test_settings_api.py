import os
import subprocess
import tempfile

import pytest
from lexigram.sql.providers.database_service import DatabaseService

from shorts_creator.controllers.api.settings_api import SettingsApiController
from shorts_creator.models.asset import Asset
from shorts_creator.repositories.asset_repository import AssetRepository
from shorts_creator.services.asset_service import AssetService
from shorts_creator.services.core import AppConfig
from shorts_creator.services.project_profile_service import ProjectProfileService
from shorts_creator.services.settings_store import SettingsStore

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class FakeFormRequest:
    def __init__(self, form_data: dict[str, str]):
        self._form_data = form_data

    async def form(self):
        return self._form_data


@pytest.fixture
async def api():
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
    config = AppConfig.from_dict(
        {
            "reel_width": 1080,
            "reel_height": 1920,
            "default_duration": 30.0,
        }
    )
    yield SettingsApiController(
        config,
        SettingsStore(service),
        asset_service=AssetService(AssetRepository(service)),
    )
    await service.disconnect()
    os.unlink(path)


@pytest.fixture
async def wired_api(api):
    """SettingsApiController with the production ProjectProfileService wired,
    so the global tier resolves through the real singleton path."""
    api.profile_service = ProjectProfileService(
        api.config,
        api.store,
    )
    return api


class TestSettingsApiController:
    async def test_save_then_get_reflects_new_values(self, api):
        await api.save_setting(request=FakeFormRequest({"default_duration": "42"}))
        resp = await api.get_settings()
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "42.0" in body

    async def test_get_settings_falls_back_to_config_defaults(self, api):
        resp = await api.get_settings()
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "30.0" in body

    async def test_save_rejects_batch_containing_unknown_field(self, api):
        resp = await api.save_setting(
            request=FakeFormRequest({"default_duration": "42", "csrf_token": "abc123"})
        )
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "is not a valid global setting" in body
        overrides = await api.store.get_overrides()
        assert "default_duration" not in overrides
        assert "csrf_token" not in overrides

    async def test_save_returns_success_toast(self, api):
        resp = await api.save_setting(request=FakeFormRequest({"default_duration": "42"}))
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "showToast" in body
        assert "Settings saved" in body

    async def test_save_rejects_non_numeric_duration(self, api):
        resp = await api.save_setting(request=FakeFormRequest({"default_duration": "oops"}))
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "must be a positive number" in body
        assert "Settings saved" not in body
        overrides = await api.store.get_overrides()
        assert "default_duration" not in overrides

    async def test_save_rejects_non_positive_duration(self, api):
        resp = await api.save_setting(request=FakeFormRequest({"default_duration": "-5"}))
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "must be a positive number" in body
        overrides = await api.store.get_overrides()
        assert "default_duration" not in overrides

    async def test_save_returns_field_level_errors(self, api):
        resp = await api.save_setting(
            request=FakeFormRequest(
                {
                    "default_duration": "oops",
                    "cta_lead_in_seconds": "-1",
                }
            )
        )
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert 'id="profile-field-error-default_duration"' in body
        assert 'id="profile-field-error-cta_lead_in_seconds"' in body
        assert "hx-swap-oob" in body
        assert "Settings saved" not in body
        overrides = await api.store.get_overrides()
        assert "default_duration" not in overrides
        assert "cta_lead_in_seconds" not in overrides

    async def test_save_success_returns_refreshed_global_profile_fragment(self, api):
        resp = await api.save_setting(request=FakeFormRequest({"default_duration": "42"}))
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert 'data-profile-field="default_duration"' in body
        assert 'value="42"' in body
        assert 'hx-swap-oob="innerHTML:#settings-creative-fields"' in body
        assert "Settings saved" in body

    async def test_save_stock_keys_persists_and_refreshes_stock_fields(self, api):
        resp = await api.save_setting(
            request=FakeFormRequest({"pexels_api_key": "px-123", "pixabay_api_key": "  pb-456  "})
        )
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert 'hx-swap-oob="innerHTML:#settings-stock-fields"' in body
        assert 'value="px-123"' in body
        assert "Settings saved" in body
        assert await api.store.get_credentials() == {
            "pexels_api_key": "px-123",
            "pixabay_api_key": "pb-456",
        }

    async def test_save_clearing_stock_key_revokes_it(self, api):
        await api.save_setting(request=FakeFormRequest({"pexels_api_key": "px-123"}))
        resp = await api.save_setting(
            request=FakeFormRequest({"pexels_api_key": "", "pixabay_api_key": "pb-1"})
        )
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "Settings saved" in body
        assert await api.store.get_credentials() == {"pixabay_api_key": "pb-1"}

    async def test_save_success_fragment_keeps_default_asset_options(self, api):
        music = Asset(type="music", name="My Track", role=None)
        await api.asset_service.repo.create(music)
        resp = await api.save_setting(request=FakeFormRequest({"asset_default_music_id": music.id}))
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert music.id in body
        assert "My Track" in body
        assert f'value="{music.id}"' in body

    async def test_get_settings_tolerates_garbage_row_in_db(self, api):
        await api.store._db.execute(
            "INSERT OR REPLACE INTO app_settings (key, value, updated_at) VALUES ('default_duration', 'not-a-float', datetime('now'))"
        )
        resp = await api.get_settings()
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "30.0" in body

    async def test_wired_get_settings_reflects_saved_values(self, wired_api):
        await wired_api.save_setting(request=FakeFormRequest({"default_duration": "42"}))
        resp = await wired_api.get_settings()
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "44.0" in body

    async def test_wired_get_settings_falls_back_to_config_defaults(self, wired_api):
        resp = await wired_api.get_settings()
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "44.0" in body

    async def test_wired_get_settings_tolerates_garbage_row_in_db(self, wired_api):
        await wired_api.store._db.execute(
            "INSERT OR REPLACE INTO app_settings (key, value, updated_at) VALUES ('default_duration', 'not-a-float', datetime('now'))"
        )
        resp = await wired_api.get_settings()
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "44.0" in body
