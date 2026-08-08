import json
from unittest.mock import MagicMock

from shorts_creator.controllers.project_settings import ProjectSettingsController
from shorts_creator.controllers.settings import SettingsController
from shorts_creator.models.asset import Asset
from shorts_creator.models.project import Project
from shorts_creator.models.project_profile import ProjectProfileOverrides
from shorts_creator.services.core import AppConfig
from shorts_creator.services.settings_store import ALLOWED_KEYS

ASSET_DEFAULT_KEYS = {
    "asset_default_music_id",
    "asset_default_font_id",
    "asset_default_watermark_id",
    "asset_default_bg_clip_id",
    "asset_default_outro_clip_id",
}


class _FakeStore:
    def __init__(self, overrides=None):
        self.overrides = overrides or {}

    async def get_overrides(self):
        return self.overrides


class _FakeAssetService:
    def __init__(self, assets=None):
        self.assets = assets or [
            Asset(type="music", name="Lo-fi", file_path="m/1.mp3"),
            Asset(type="font", name="Inter", file_path="f/1.ttf"),
        ]

    async def list_by_type(self, asset_type, role=None):
        return [a for a in self.assets if a.type == asset_type and (role is None or a.role == role)]


class _FakeLayout:
    def render(self, content="", title="", request=None):
        return f"<html>{title}|{content}</html>"


class _FakeProjects:
    def __init__(self, project):
        self._project = project

    async def get(self, project_id):
        return self._project

    async def update(self, project_id, updates):
        for k, v in updates.items():
            setattr(self._project, k, v)
        return self._project

    def _overrides(self):
        try:
            overrides = json.loads(self._project.profile_overrides_json or "{}")
            return overrides if isinstance(overrides, dict) else {}
        except (TypeError, ValueError):
            return {}

    async def save_profile_overrides(self, project_id, updates: ProjectProfileOverrides):
        merged = {**self._overrides()}
        for key, value in updates.model_dump(exclude_none=True).items():
            if value == "":
                merged.pop(key, None)
            else:
                merged[key] = value
        self._project.profile_overrides_json = json.dumps(merged, separators=(",", ":"))
        return self._project


class _FakeFormRequest:
    def __init__(self, form_data: dict):
        self._form_data = form_data

    async def form(self):
        return self._form_data


class TestSettingsStoreKeys:
    def test_asset_default_keys_are_allowed(self):
        assert ASSET_DEFAULT_KEYS <= ALLOWED_KEYS


class TestGlobalDefaultsPage:
    async def test_settings_page_has_asset_selectors(self):
        config = AppConfig.from_dict(
            {"reel_width": 1080, "reel_height": 1920, "default_duration": 30.0}
        )
        c = SettingsController(config, _FakeStore())
        c.layout = _FakeLayout()
        c.llm_config = MagicMock(providers=[])
        req = MagicMock()
        req.query_params = {"tab": "global"}
        req.headers = {}
        resp = await c.view_settings(request=req)
        html = resp.body if hasattr(resp, "body") else str(resp)
        assert "Default Music" in html
        assert "Default Font" in html
        assert "Default Watermark" in html
        assert "Default Background Clip" in html
        assert "Default Outro Clip" in html

    async def test_global_selects_list_assets(self):
        config = AppConfig.from_dict(
            {"reel_width": 1080, "reel_height": 1920, "default_duration": 30.0}
        )
        c = SettingsController(config, _FakeStore(), _FakeAssetService())
        c.layout = _FakeLayout()
        c.llm_config = MagicMock(providers=[])
        req = MagicMock()
        req.query_params = {"tab": "global"}
        req.headers = {}
        resp = await c.view_settings(request=req)
        html = resp.body if hasattr(resp, "body") else str(resp)
        assert "Lo-fi" in html
        assert 'name="asset_default_music_id"' in html

    async def test_global_selects_preselect_saved_value(self):
        config = AppConfig.from_dict(
            {"reel_width": 1080, "reel_height": 1920, "default_duration": 30.0}
        )
        music = Asset(type="music", name="Lo-fi", file_path="m/1.mp3")
        c = SettingsController(
            config, _FakeStore({"asset_default_music_id": music.id}), _FakeAssetService([music])
        )
        c.layout = _FakeLayout()
        c.llm_config = MagicMock(providers=[])
        req = MagicMock()
        req.query_params = {"tab": "global"}
        req.headers = {}
        resp = await c.view_settings(request=req)
        html = resp.body if hasattr(resp, "body") else str(resp)
        assert f'value="{music.id}" selected' in html

    async def test_settings_page_shows_stock_provider_keys(self, monkeypatch):
        monkeypatch.setenv("PEXELS_API_KEY", "env-px")
        config = AppConfig.from_dict(
            {"reel_width": 1080, "reel_height": 1920, "default_duration": 30.0}
        )
        c = SettingsController(config, _FakeStore({"pixabay_api_key": "pb-456"}))
        c.layout = _FakeLayout()
        c.llm_config = MagicMock(providers=[])
        req = MagicMock()
        req.query_params = {"tab": "global"}
        req.headers = {}
        resp = await c.view_settings(request=req)
        html = resp.body if hasattr(resp, "body") else str(resp)
        assert 'id="settings-stock-fields"' in html
        assert 'name="pexels_api_key"' in html
        assert 'placeholder="Set via environment"' in html
        assert 'value="pb-456"' in html
        assert "Configured" in html


class TestProjectSettingsPage:
    async def test_project_settings_has_asset_selectors(self):
        config = AppConfig.from_dict(
            {"reel_width": 1080, "reel_height": 1920, "default_duration": 30.0}
        )
        project = Project(topic="self_improvement")
        c = ProjectSettingsController(config, _FakeProjects(project), _FakeStore())
        c.layout = _FakeLayout()
        req = MagicMock()
        req.query_params = {}
        req.headers = {}
        resp = await c.project_settings(request=req, id=project.id)
        html = resp.body if hasattr(resp, "body") else str(resp)
        assert 'name="asset_music_id"' in html
        assert 'name="asset_outro_clip_id"' in html
        assert 'name="asset_bg_clip_id"' in html
        assert "Inherit" in html

    async def test_project_save_persists_asset_selection(self):
        config = AppConfig.from_dict(
            {"reel_width": 1080, "reel_height": 1920, "default_duration": 30.0}
        )
        project = Project(topic="self_improvement")
        projects = _FakeProjects(project)
        c = ProjectSettingsController(config, projects, _FakeStore())
        await c.save_project_settings(
            request=_FakeFormRequest({"asset_music_id": "music-1", "asset_bg_clip_id": ""}),
            id=project.id,
        )
        assert project.asset_music_id == "music-1"
        assert project.asset_bg_clip_id is None
