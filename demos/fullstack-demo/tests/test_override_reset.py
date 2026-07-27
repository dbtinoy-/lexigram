"""Override reset buttons must actually reset, on both settings surfaces."""

import json
import os
import subprocess
import tempfile

import pytest
from lexigram.sql.providers.database_service import DatabaseService

from shorts_creator.controllers.api.settings_api import SettingsApiController
from shorts_creator.controllers.project_settings import ProjectSettingsController
from shorts_creator.models.project import Project
from shorts_creator.models.project_profile import ProjectProfileOverrides
from shorts_creator.repositories.project_repository import ProjectRepository
from shorts_creator.services.core import AppConfig
from shorts_creator.services.project_profile_service import ProjectProfileService
from shorts_creator.services.project_service import ProjectService
from shorts_creator.services.settings_store import ALLOWED_KEYS, SettingsStore

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class FakeFormRequest:
    def __init__(self, form_data: dict[str, str]):
        self._form_data = form_data

    async def form(self):
        return self._form_data


@pytest.fixture
async def services():
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
    settings_api = SettingsApiController(config, store, profile_service=profile_service)
    project_settings = ProjectSettingsController(
        config, projects, store, profile_service=profile_service
    )
    yield projects, store, settings_api, project_settings
    await service.disconnect()
    os.unlink(path)


def _body(resp) -> str:
    body = resp.body if hasattr(resp, "body") else str(resp)
    return body.decode() if isinstance(body, bytes) else body


def _overrides(project) -> dict:
    try:
        return json.loads(project.profile_overrides_json or "{}")
    except (TypeError, ValueError):
        return {}


class TestStoreReset:
    async def test_reset_removes_key(self, services):
        _, store, _, _ = services
        await store.save({"default_caption_style": "list"})
        await store.reset("default_caption_style")
        assert "default_caption_style" not in await store.get_overrides()


class TestProjectResetEndpoint:
    async def test_resets_single_override(self, services):
        projects, _, _, controller = services
        project = await projects.repo.create(Project(topic="self_improvement"))
        await projects.save_profile_overrides(
            project.id,
            ProjectProfileOverrides(duration_seconds=45.0, hook_text="x"),
        )
        resp = await controller.reset_override(
            FakeFormRequest({"key": "duration_seconds"}), id=project.id
        )
        assert "Override reset" in _body(resp)
        remaining = _overrides(await projects.repo.get(project.id))
        assert "duration_seconds" not in remaining
        assert remaining.get("hook_text") == "x"

    async def test_unknown_key_is_safe_noop(self, services):
        projects, _, _, controller = services
        project = await projects.repo.create(Project(topic="self_improvement"))
        resp = await controller.reset_override(
            FakeFormRequest({"key": "no_such_key"}), id=project.id
        )
        assert "Override reset" in _body(resp)

    async def test_missing_key_rejected(self, services):
        projects, _, _, controller = services
        project = await projects.repo.create(Project(topic="self_improvement"))

        resp = await controller.reset_override(FakeFormRequest({}), id=project.id)
        assert resp is not None and "key" in _body(resp).lower()

    async def test_unknown_project_404(self, services):
        _, _, _, controller = services

        resp = await controller.reset_override(
            FakeFormRequest({"key": "hook_text"}), id="00000000-0000-0000-0000-000000000000"
        )
        assert _body(resp) == "Project not found"


class TestGlobalResetEndpoint:
    async def test_reset_removes_stored_value(self, services):
        _, store, controller, _ = services
        await store.save({"default_caption_style": "list", "default_duration": "45"})
        await controller.reset_override(FakeFormRequest({"key": "default_caption_style"}))
        overrides = await store.get_overrides()
        assert "default_caption_style" not in overrides
        assert overrides.get("default_duration") == "45"

    async def test_reset_response_rerenders_fields_without_button(self, services):
        _, store, controller, _ = services
        await store.save({"default_caption_style": "list"})
        resp = await controller.reset_override(FakeFormRequest({"key": "default_caption_style"}))
        body = _body(resp)
        assert 'data-override-toggle data-key="default_caption_style"' not in body


class TestGlobalPageRendersResetButtons:
    async def test_overridden_field_gets_reset_button_with_url(self, services):
        from shorts_creator.controllers.settings import render_global_creative_fields

        _, store, _, _ = services
        await store.save({"default_caption_style": "list"})
        overrides = await store.get_overrides()
        fields = await render_global_creative_fields(AppConfig(), overrides, asset_service=None)
        assert 'data-override-toggle data-key="default_caption_style"' in fields
        assert 'data-reset-url="/api/settings/reset-override"' in fields

    async def test_inherited_field_has_no_reset_button(self, services):
        from shorts_creator.controllers.settings import render_global_creative_fields

        fields = await render_global_creative_fields(AppConfig(), {}, asset_service=None)
        assert "data-override-toggle" not in fields

    async def test_stored_empty_value_shows_builtin_badge_and_no_reset(self, services):
        from shorts_creator.controllers.settings import render_global_creative_fields

        _, store, _, _ = services
        await store._db.execute(
            "INSERT OR REPLACE INTO app_settings (key, value, updated_at) "
            "VALUES ('default_caption_style', '', datetime('now'))"
        )
        overrides = await store.get_overrides()
        assert overrides.get("default_caption_style") == ""
        fields = await render_global_creative_fields(AppConfig(), overrides, asset_service=None)
        assert 'data-source="built_in"' in fields
        assert "data-override-toggle" not in fields


class TestProjectPageRendersResetButtons:
    async def test_overridden_field_gets_reset_button_with_project_url(self, services):
        projects, _, _, controller = services
        project = await projects.repo.create(Project(topic="self_improvement"))
        await projects.save_profile_overrides(
            project.id, ProjectProfileOverrides(duration_seconds=45.0)
        )

        body = _body(await controller.project_settings(request=None, id=project.id))

        assert 'data-override-toggle data-key="duration_seconds"' in body
        assert f'data-reset-url="/api/projects/{project.id}/reset-override"' in body

    async def test_inherited_project_page_has_no_reset_button(self, services):
        projects, _, _, controller = services
        project = await projects.repo.create(Project(topic="self_improvement"))

        body = _body(await controller.project_settings(request=None, id=project.id))

        assert "data-override-toggle" not in body


class TestGlobalResetAllowlist:
    async def test_every_allowlisted_key_resets_only_that_row(self, services):
        _, store, controller, _ = services
        allowed = sorted(ALLOWED_KEYS)
        for key in allowed:
            seed = {
                k: (
                    "45"
                    if k == "default_duration"
                    else "list"
                    if k == "default_caption_style"
                    else "42"
                )
                for k in allowed
            }
            await store.save(seed)
            resp = await controller.reset_override(FakeFormRequest({"key": key}))
            assert "Override reset" in _body(resp)
            remaining = await store.get_overrides()
            assert key not in remaining
            assert set(remaining) == set(allowed) - {key}

    async def test_non_allowlisted_key_is_noop_success(self, services):
        _, store, controller, _ = services
        await store.save_global_values({"pexels_api_key": "sk-test-123"})
        resp = await controller.reset_override(FakeFormRequest({"key": "pexels_api_key"}))
        assert "Override reset" in _body(resp)
        assert (await store.get_overrides()).get("pexels_api_key") == "sk-test-123"

    async def test_store_reset_gated_to_render_allowlist(self, services):
        _, store, _, _ = services
        await store.save_global_values({"pixabay_api_key": "pk-xyz"})
        await store.reset("pixabay_api_key")
        assert (await store.get_overrides()).get("pixabay_api_key") == "pk-xyz"
