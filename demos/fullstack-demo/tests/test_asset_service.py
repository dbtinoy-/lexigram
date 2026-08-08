import pytest

from shorts_creator.models.asset import Asset
from shorts_creator.services.asset_service import VALID_EXTENSIONS, AssetService


class _FakeRepo:
    def __init__(self):
        self.items = []

    async def create(self, asset: Asset) -> Asset:
        self.items.append(asset)
        return asset

    async def get(self, asset_id: str):
        return next((a for a in self.items if a.id == asset_id), None)

    async def update(self, asset_id: str, updates: dict):
        asset = await self.get(asset_id)
        if not asset:
            return None
        for k, v in updates.items():
            setattr(asset, k, v)
        return asset

    async def delete(self, asset_id: str):
        asset = await self.get(asset_id)
        if asset:
            self.items.remove(asset)
            return True
        return False

    async def list_by_type(self, asset_type, role=None):
        return [a for a in self.items if a.type == asset_type and (role is None or a.role == role)]

    async def list_all(self):
        return list(self.items)


class _FailingCreateRepo(_FakeRepo):
    async def create(self, asset: Asset) -> Asset:
        raise RuntimeError("boom")


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr("shorts_creator.services.asset_service.ASSETS_ROOT", tmp_path)
    return AssetService(_FakeRepo())


class TestAssetServiceUpload:
    async def test_upload_writes_file_and_registers_asset(self, service, tmp_path):
        asset = await service.create_asset(
            "music",
            "Lo-fi",
            b"RIFF-fake-audio",
            ext="mp3",
            description="Chill beat",
            tags=["chill"],
        )
        assert asset.file_path is not None
        assert asset.file_path.startswith("music/")
        stored = (tmp_path / asset.file_path).read_bytes()
        assert stored == b"RIFF-fake-audio"
        assert asset.meta["mime"] == "audio/mpeg"
        assert asset.meta["size_bytes"] == len(b"RIFF-fake-audio")

    async def test_rejects_bad_extension(self, service):
        with pytest.raises(ValueError, match="extension"):
            await service.create_asset("music", "Bad", b"x", ext="exe")

    async def test_rejects_oversized_file(self, service):
        with pytest.raises(ValueError, match="too large"):
            await service.create_asset("font", "Huge", b"x" * (6 * 1024 * 1024), ext="ttf")

    async def test_unknown_type_rejected(self, service):
        with pytest.raises(ValueError, match="type"):
            await service.create_asset("theme", "T", b"x", ext="png")

    async def test_delete_removes_file(self, service, tmp_path):
        asset = await service.create_asset("image", "Pic", b"png-bytes", ext="png")
        assert (tmp_path / asset.file_path).exists()
        await service.delete_asset(asset.id)
        assert not (tmp_path / asset.file_path).exists()

    async def test_rejects_empty_file(self, service):
        with pytest.raises(ValueError, match="Empty file"):
            await service.create_asset("image", "Pic", b"", ext="png")

    async def test_ext_is_normalized(self, service, tmp_path):
        asset = await service.create_asset("image", "Pic", b"png-bytes", ext=".PNG")
        assert asset.file_path.endswith(".png")
        assert asset.meta["ext"] == "png"
        assert (tmp_path / asset.file_path).exists()

    async def test_create_failure_removes_written_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("shorts_creator.services.asset_service.ASSETS_ROOT", tmp_path)
        service = AssetService(_FailingCreateRepo())
        with pytest.raises(RuntimeError, match="boom"):
            await service.create_asset("image", "Pic", b"png-bytes", ext="png")
        assert list(tmp_path.rglob("*.png")) == []

    async def test_delete_without_row_keeps_file(self, service, tmp_path):
        asset = await service.create_asset("image", "Pic", b"png-bytes", ext="png")
        service.repo.items.remove(asset)
        result = await service.delete_asset(asset.id)
        assert result is False
        assert (tmp_path / asset.file_path).exists()


class TestAssetServiceValidationTable:
    def test_extensions_table_shape(self):
        assert VALID_EXTENSIONS["music"] == ("mp3", "wav", "m4a")
        assert VALID_EXTENSIONS["font"] == ("ttf", "otf")
        assert VALID_EXTENSIONS["image"] == ("png", "jpg", "jpeg", "webp")
        assert VALID_EXTENSIONS["clip"] == ("mp4", "mov", "webm")
        assert VALID_EXTENSIONS["watermark"] == ("png", "webp")
