import os
import subprocess
import tempfile

import pytest
from lexigram.sql.providers.database_service import DatabaseService

from shorts_creator.models.asset import Asset
from shorts_creator.repositories.asset_repository import AssetRepository

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
async def repo():
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
    yield AssetRepository(service)
    await service.disconnect()
    os.unlink(path)


class TestAssetRepository:
    async def test_create_and_get_roundtrip(self, repo):
        asset = Asset(
            type="music",
            name="Lo-fi",
            file_path="music/abc.mp3",
            meta={"duration_s": 10.5},
            tags=["chill"],
        )
        created = await repo.create(asset)
        fetched = await repo.get(created.id)
        assert fetched is not None
        assert fetched.name == "Lo-fi"
        assert fetched.meta == {"duration_s": 10.5}
        assert fetched.tags == ["chill"]

    async def test_list_by_type_and_role(self, repo):
        outro = Asset(type="clip", name="End Card", role="outro", file_path="clip/1.mp4")
        bg = Asset(type="clip", name="Forest", role="background", file_path="clip/2.mp4")
        await repo.create(outro)
        await repo.create(bg)

        clips = await repo.list_by_type("clip")
        assert len(clips) == 2
        outros = await repo.list_by_type("clip", role="outro")
        assert len(outros) == 1 and outros[0].name == "End Card"

    async def test_update_persists_fields(self, repo):
        asset = await repo.create(Asset(type="font", name="Inter", file_path="font/1.ttf"))
        await repo.update(asset.id, {"name": "Inter Bold"})
        fetched = await repo.get(asset.id)
        assert fetched.name == "Inter Bold"

    async def test_delete_removes_row(self, repo):
        asset = await repo.create(Asset(type="watermark", name="Logo", file_path="wm/1.png"))
        assert await repo.delete(asset.id) is True
        assert await repo.get(asset.id) is None
