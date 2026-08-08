import json
import os
import subprocess
import tempfile

import pytest
from lexigram.sql.providers.database_service import DatabaseService

from shorts_creator.controllers.project_settings import ProjectSettingsController
from shorts_creator.models.project import Project
from shorts_creator.repositories.project_repository import ProjectRepository
from shorts_creator.services.core import AppConfig
from shorts_creator.services.project_profile_service import ProjectProfileService
from shorts_creator.services.project_service import ProjectService
from shorts_creator.services.settings_store import SettingsStore

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class FakeFormRequest:
    def __init__(self, form_data: dict[str, str]):
        self._form_data = form_data

    async def form(self):
        return self._form_data


@pytest.fixture
async def controller_and_service():
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
    projects = ProjectService(ProjectRepository(service))
    store = SettingsStore(service)
    profile_service = ProjectProfileService(config, store)
    controller = ProjectSettingsController(config, projects, store, profile_service=profile_service)
    yield controller, projects
    await service.disconnect()
    os.unlink(path)


def _body(resp) -> str:
    return resp.body if hasattr(resp, "body") else str(resp)


def _overrides(project) -> dict:
    try:
        return json.loads(project.profile_overrides_json or "{}")
    except (TypeError, ValueError):
        return {}


class TestSaveProjectSettings:
    async def test_full_profile_save_persists_overrides(self, controller_and_service):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))

        resp = await controller.save_project_settings(
            request=FakeFormRequest(
                {
                    "duration_seconds": "42",
                    "caption_style": "plain",
                    "format_name": "narrated",
                    "asset_music_id": "music-1",
                    "asset_bg_clip_id": "",
                }
            ),
            id=project.id,
        )

        assert "saved" in _body(resp).lower()
        saved = await projects.get(project.id)
        assert _overrides(saved) == {
            "duration_seconds": 42.0,
            "caption_style": "plain",
            "asset_music_id": "music-1",
        }

    async def test_save_keeps_unsubmitted_keys(self, controller_and_service):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))
        project.profile_overrides_json = json.dumps(
            {"duration_seconds": 30, "caption_style": "plain"}
        )
        await projects.repo.update(project)

        await controller.save_project_settings(
            request=FakeFormRequest({"caption_style": "highlight"}),
            id=project.id,
        )

        saved = await projects.get(project.id)
        assert _overrides(saved) == {"duration_seconds": 30.0, "caption_style": "highlight"}

    async def test_save_rejects_invalid_duration(self, controller_and_service):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))

        resp = await controller.save_project_settings(
            request=FakeFormRequest({"duration_seconds": "-5"}),
            id=project.id,
        )

        body = _body(resp)
        assert "Could not save" in body
        assert "duration_seconds" in body
        assert 'id="profile-field-error-duration_seconds"' in body
        assert "hx-swap-oob" in body
        assert _overrides(await projects.get(project.id)) == {}

    async def test_save_ignores_legacy_cta_keys(self, controller_and_service):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))

        resp = await controller.save_project_settings(
            request=FakeFormRequest(
                {
                    "duration_seconds": "10",
                    "cta_lead_in_seconds": "5",
                    "cta_display_seconds": "20",
                }
            ),
            id=project.id,
        )

        body = _body(resp)
        assert "saved" in body.lower()
        assert _overrides(await projects.get(project.id)) == {"duration_seconds": 10.0}

    async def test_save_missing_project_returns_404(self, controller_and_service):
        controller, _ = controller_and_service
        resp = await controller.save_project_settings(request=FakeFormRequest({}), id="missing")
        assert resp.status_code == 404

    async def test_save_persists_format_and_duration_from_wizard(self, controller_and_service):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))

        resp = await controller.save_project_settings(
            request=FakeFormRequest(
                {
                    "format": "steps",
                    "duration_seconds": "48",
                    "caption_style": "plain",
                }
            ),
            id=project.id,
        )

        assert "saved" in _body(resp).lower()
        saved = await projects.get(project.id)
        overrides = _overrides(saved)
        assert overrides["format_name"] == "steps"
        assert overrides["duration_seconds"] == 48.0
        assert overrides["caption_style"] == "plain"

    async def test_save_matching_inherited_values_adds_no_overrides(self, controller_and_service):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))

        resp = await controller.save_project_settings(
            request=FakeFormRequest(
                {
                    "format": "narrated",
                    # inherited duration for a fresh self_improvement project resolves to the
                    # narrated format midpoint 44.0 (data/formats/narrated/FORMAT.md range [38,50]),
                    # so "44" means "save untouched"
                    "duration_seconds": "44",
                    "caption_style": "highlight",
                }
            ),
            id=project.id,
        )

        assert "saved" in _body(resp).lower()
        assert _overrides(await projects.get(project.id)) == {}

    async def test_save_captionless_format_clears_stale_caption_style_override(
        self, controller_and_service
    ):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))
        project.profile_overrides_json = json.dumps({"caption_style": "plain"})
        await projects.repo.update(project)

        resp = await controller.save_project_settings(
            request=FakeFormRequest(
                {
                    "format": "steps",
                    "caption_style": "",
                }
            ),
            id=project.id,
        )

        assert "saved" in _body(resp).lower()
        assert _overrides(await projects.get(project.id)) == {"format_name": "steps"}

    async def test_save_captionless_format_does_not_persist_blank_caption_style(
        self, controller_and_service
    ):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))

        resp = await controller.save_project_settings(
            request=FakeFormRequest(
                {
                    "format": "steps",
                    "caption_style": "",
                }
            ),
            id=project.id,
        )

        assert "saved" in _body(resp).lower()
        assert _overrides(await projects.get(project.id)) == {"format_name": "steps"}

    async def test_save_url_source_clears_stale_asset_override(self, controller_and_service):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))
        project.profile_overrides_json = json.dumps({"asset_music_id": "music-1"})
        await projects.repo.update(project)

        resp = await controller.save_project_settings(
            request=FakeFormRequest(
                {
                    "media_source_music": "url",
                    "media_url_music": "https://cdn.example.com/bed.mp3",
                    "asset_music_id": "music-1",
                }
            ),
            id=project.id,
        )

        assert "saved" in _body(resp).lower()
        overrides = _overrides(await projects.get(project.id))
        assert overrides.get("media_url_music") == "https://cdn.example.com/bed.mp3"
        assert overrides.get("asset_music_id", "") == ""

    async def test_save_assets_source_clears_stale_url_override(self, controller_and_service):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))
        project.profile_overrides_json = json.dumps(
            {"media_url_music": "https://old.example/x.mp3"}
        )
        await projects.repo.update(project)

        resp = await controller.save_project_settings(
            request=FakeFormRequest(
                {
                    "media_source_music": "assets",
                    "asset_music_id": "music-2",
                }
            ),
            id=project.id,
        )

        assert "saved" in _body(resp).lower()
        overrides = _overrides(await projects.get(project.id))
        assert overrides.get("asset_music_id") == "music-2"
        assert overrides.get("media_url_music", "") == ""

    async def test_save_bg_url_clears_asset_and_api_state(self, controller_and_service):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))
        project.profile_overrides_json = json.dumps(
            {"asset_bg_clip_id": "bg-1", "bg_source": "api", "stock_provider": "pexels"}
        )
        await projects.repo.update(project)

        resp = await controller.save_project_settings(
            request=FakeFormRequest(
                {
                    "media_source_bg_clip": "url",
                    "media_url_bg_clip": "https://cdn.example.com/bg.mp4",
                }
            ),
            id=project.id,
        )

        assert "saved" in _body(resp).lower()
        overrides = _overrides(await projects.get(project.id))
        assert overrides.get("media_url_bg_clip") == "https://cdn.example.com/bg.mp4"
        assert overrides.get("asset_bg_clip_id", "") == ""
        assert overrides.get("bg_source", "") == ""
        assert overrides.get("stock_provider", "") == ""

    async def test_save_api_source_clears_bg_url_and_asset(self, controller_and_service):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))
        project.profile_overrides_json = json.dumps(
            {"asset_bg_clip_id": "bg-1", "media_url_bg_clip": "https://old.example/bg.mp4"}
        )
        await projects.repo.update(project)

        resp = await controller.save_project_settings(
            request=FakeFormRequest(
                {
                    "media_source_bg_clip": "api",
                    "stock_provider_bg_clip": "pexels",
                }
            ),
            id=project.id,
        )

        assert "saved" in _body(resp).lower()
        overrides = _overrides(await projects.get(project.id))
        assert overrides.get("bg_source") == "api"
        assert overrides.get("stock_provider") == "pexels"
        assert overrides.get("asset_bg_clip_id", "") == ""
        assert overrides.get("media_url_bg_clip", "") == ""

    async def test_save_url_source_for_outro_persists_consumer_key(self, controller_and_service):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))
        project.profile_overrides_json = json.dumps({"asset_outro_clip_id": "outro-1"})
        await projects.repo.update(project)

        resp = await controller.save_project_settings(
            request=FakeFormRequest(
                {
                    "media_source_outro_clip": "url",
                    "media_url_outro_clip": "https://cdn.example.com/outro.mp4",
                    "asset_outro_clip_id": "outro-1",
                }
            ),
            id=project.id,
        )

        assert "saved" in _body(resp).lower()
        overrides = _overrides(await projects.get(project.id))
        assert overrides.get("media_url_outro") == "https://cdn.example.com/outro.mp4"
        assert overrides.get("asset_outro_clip_id", "") == ""

    async def test_save_blank_pacing_clears_override_without_500(self, controller_and_service):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))
        project.profile_overrides_json = json.dumps({"pacing_wps": 2.7})
        await projects.repo.update(project)

        resp = await controller.save_project_settings(
            request=FakeFormRequest(
                {
                    "pacing_wps": "",
                    "caption_style": "highlight",
                }
            ),
            id=project.id,
        )

        assert "saved" in _body(resp).lower()
        assert _overrides(await projects.get(project.id)) == {}

    async def test_save_auto_asset_select_removes_asset_and_url_overrides(
        self, controller_and_service
    ):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))
        project.profile_overrides_json = json.dumps(
            {
                "asset_music_id": "music-1",
                "media_url_music": "https://cdn.example.com/bed.mp3",
            }
        )
        await projects.repo.update(project)

        resp = await controller.save_project_settings(
            request=FakeFormRequest(
                {
                    "media_source_music": "assets",
                    "asset_music_id": "",
                    "media_url_music": "",
                }
            ),
            id=project.id,
        )

        assert "saved" in _body(resp).lower()
        overrides = _overrides(await projects.get(project.id))
        assert "asset_music_id" not in overrides
        assert "media_url_music" not in overrides


class TestProjectSettingsPage:
    async def test_page_renders_composer_settings_form(self, controller_and_service):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))

        resp = await controller.project_settings(request=None, id=project.id)
        body = _body(resp)

        assert 'id="project-profile-form"' in body
        assert f'action="/api/projects/{project.id}/settings"' in body
        assert f'hx-post="/api/projects/{project.id}/settings"' in body
        assert 'hx-target="#project-settings-feedback"' in body
        assert 'id="profile-save-btn"' in body
        assert "Save Settings" in body
        assert 'id="profile-save-indicator"' in body

    async def test_page_shows_profile_summary_and_media_pickers(self, controller_and_service):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))

        resp = await controller.project_settings(request=None, id=project.id)
        body = _body(resp)

        assert 'id="profile-summary"' in body
        assert "Customized" in body and "Inherited" in body
        assert 'name="asset_music_id"' in body
        assert 'name="asset_bg_clip_id"' in body
        assert "Auto (default)" in body

    async def test_page_renders_without_assets(self, controller_and_service):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))

        resp = await controller.project_settings(request=None, id=project.id)
        body = _body(resp)

        assert 'name="asset_music_id"' in body
        assert "Inherit" in body

    async def test_page_renders_editable_wizard_fields(self, controller_and_service):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))

        resp = await controller.project_settings(request=None, id=project.id)
        body = _body(resp)

        assert 'data-format="narrated"' in body
        assert 'data-format="steps"' in body
        assert 'name="duration_seconds"' in body
        assert 'name="caption_style"' in body
        assert 'data-style="highlight"' in body
        assert 'data-style="plain"' in body
        assert 'src="/static/js/project-form.js"' in body
        assert "window.__COMPATIBLE_JSON__" in body
        assert body.count('id="duration-range-hint"') == 1

    async def test_page_does_not_emit_named_hidden_composites(self, controller_and_service):
        controller, projects = controller_and_service
        project = await projects.repo.create(Project(topic="self_improvement"))

        resp = await controller.project_settings(request=None, id=project.id)
        body = _body(resp)

        # named wizard fields replace the no-name composites; the type/title
        # composites must remain (JS preview reads #new-project-type)
        assert 'name="format"' in body
        assert 'id="new-project-format"' in body
        assert 'id="new-project-type"' in body
