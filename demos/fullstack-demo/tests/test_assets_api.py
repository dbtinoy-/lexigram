import os
import subprocess
import tempfile

import pytest
from lexigram.sql.providers.database_service import DatabaseService

from shorts_creator.controllers.api.assets_api import AssetsApiController
from shorts_creator.repositories.asset_repository import AssetRepository
from shorts_creator.services.asset_service import AssetService

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class FakeUploadFile:
    def __init__(self, filename: str, data: bytes):
        self.filename = filename
        self._data = data

    async def read(self):
        return self._data


class FakeFormRequest:
    def __init__(self, form_data: dict):
        self._form_data = form_data

    async def form(self):
        return self._form_data


@pytest.fixture
async def api(tmp_path, monkeypatch):
    monkeypatch.setattr("shorts_creator.services.asset_service.ASSETS_ROOT", tmp_path)
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_url = f"sqlite:///{path}"
    alembic_url = f"sqlite+aiosqlite:///{path}"
    subprocess.run(
        [".venv/bin/alembic", "-c", "migrations/primary/alembic.ini", "upgrade", "head"],
        cwd=REPO_ROOT,
        env={**os.environ, "SHORTS_CREATOR_DATABASE_URL": alembic_url},
        check=True,
        capture_output=True,
    )
    service = DatabaseService(db_url)
    await service.connect()
    yield AssetsApiController(AssetService(AssetRepository(service)))
    await service.disconnect()
    os.unlink(path)


class TestAssetsApi:
    async def test_upload_creates_asset(self, api):
        resp = await api.upload(
            request=FakeFormRequest(
                {
                    "type": "font",
                    "name": "Inter",
                    "file": FakeUploadFile("inter.ttf", b"fake-ttf"),
                }
            )
        )
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "saved" in body.lower()
        assets = await api.service.list_by_type("font")
        assert len(assets) == 1
        assert assets[0].name == "Inter"

    async def test_upload_rejects_bad_extension(self, api):
        resp = await api.upload(
            request=FakeFormRequest(
                {
                    "type": "font",
                    "name": "Bad",
                    "file": FakeUploadFile("inter.exe", b"fake"),
                }
            )
        )
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "Invalid extension" in body

    async def test_update_and_delete(self, api):
        asset = await api.service.create_asset("image", "Pic", b"png", ext="png")
        await api.update(
            request=FakeFormRequest({"name": "Renamed", "description": "d"}), id=asset.id
        )
        fetched = await api.service.get(asset.id)
        assert fetched.name == "Renamed"

        await api.delete(request=None, id=asset.id)
        assert await api.service.get(asset.id) is None

    async def test_select_options_filters_by_type_and_role(self, api):
        await api.service.create_asset("clip", "End Card", b"clip", ext="mp4", role="outro")
        await api.service.create_asset("clip", "Forest", b"clip2", ext="mp4", role="background")
        resp = await api.select_options(
            request=type("R", (), {"query_params": {"type": "clip", "role": "outro"}})()
        )
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "End Card" in body
        assert "Forest" not in body

    async def test_select_options_has_none_option(self, api):
        resp = await api.select_options(
            request=type("R", (), {"query_params": {"type": "music"}})()
        )
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "None (built-in)" in body

    async def test_file_serving(self, api, tmp_path):
        asset = await api.service.create_asset("image", "Pic", b"\x89PNG-bytes", ext="png")
        resp = await api.file(request=None, id=asset.id)
        assert resp.path == str(tmp_path / asset.file_path)

    async def test_upload_rejects_invalid_role(self, api):
        resp = await api.upload(
            request=FakeFormRequest(
                {
                    "type": "clip",
                    "name": "Bad",
                    "role": "garbage",
                    "file": FakeUploadFile("clip.mp4", b"fake"),
                }
            )
        )
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "failed" in body.lower()

    async def test_update_ignores_invalid_role(self, api):
        asset = await api.service.create_asset("clip", "Clip", b"clip", ext="mp4", role="outro")
        await api.update(request=FakeFormRequest({"role": "garbage"}), id=asset.id)
        assert (await api.service.get(asset.id)).role == "outro"

    async def test_update_with_blank_role_keeps_stored_role(self, api):
        asset = await api.service.create_asset(
            "clip", "Clip", b"clip", ext="mp4", role="background"
        )
        await api.update(request=FakeFormRequest({"name": "Renamed", "role": ""}), id=asset.id)
        fetched = await api.service.get(asset.id)
        assert fetched.name == "Renamed"
        assert fetched.role == "background"

    async def test_update_with_new_role_writes_role(self, api):
        asset = await api.service.create_asset(
            "clip", "Clip", b"clip", ext="mp4", role="background"
        )
        await api.update(request=FakeFormRequest({"role": "outro"}), id=asset.id)
        assert (await api.service.get(asset.id)).role == "outro"

    async def test_update_and_delete_not_found(self, api):
        resp = await api.update(request=FakeFormRequest({"name": "Missing"}), id="does-not-exist")
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "not found" in body.lower()

        resp = await api.delete(request=None, id="does-not-exist")
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "not found" in body.lower()

    async def test_file_404_for_unknown_asset(self, api):
        resp = await api.file(request=None, id="does-not-exist")
        assert resp.status_code == 404
