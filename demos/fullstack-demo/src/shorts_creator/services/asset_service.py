from pathlib import Path

from shorts_creator.models.asset import ASSET_TYPES, CLIP_ROLES, Asset

ASSETS_ROOT = Path(__file__).resolve().parents[3] / "data" / "assets"

VALID_EXTENSIONS = {
    "music": ("mp3", "wav", "m4a"),
    "font": ("ttf", "otf"),
    "image": ("png", "jpg", "jpeg", "webp"),
    "clip": ("mp4", "mov", "webm"),
    "watermark": ("png", "webp"),
}

MAX_BYTES = {
    "music": 50 * 1024 * 1024,
    "font": 5 * 1024 * 1024,
    "image": 20 * 1024 * 1024,
    "clip": 500 * 1024 * 1024,
    "watermark": 20 * 1024 * 1024,
}

MIME_BY_EXT = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "m4a": "audio/mp4",
    "ttf": "font/ttf",
    "otf": "font/otf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "webm": "video/webm",
}


class AssetService:
    def __init__(self, repo):
        self.repo = repo

    @staticmethod
    def absolute_path(file_path: str) -> Path:
        return ASSETS_ROOT / file_path

    async def get(self, asset_id: str) -> Asset | None:
        return await self.repo.get(asset_id)

    async def list_by_type(self, asset_type: str, role: str | None = None) -> list[Asset]:
        return await self.repo.list_by_type(asset_type, role)

    async def list_all(self) -> list[Asset]:
        return await self.repo.list_all()

    async def create_asset(
        self,
        asset_type: str,
        name: str,
        data: bytes,
        ext: str,
        description: str = "",
        tags: list[str] | None = None,
        role: str | None = None,
    ) -> Asset:
        if asset_type not in ASSET_TYPES:
            raise ValueError(f"Unsupported asset type: {asset_type}")
        if role and role not in CLIP_ROLES:
            raise ValueError(f"Invalid role: {role} (allowed: {', '.join(CLIP_ROLES)})")
        ext = ext.lower().lstrip(".")
        if ext not in VALID_EXTENSIONS[asset_type]:
            raise ValueError(
                f"Invalid extension .{ext} for {asset_type} (allowed: "
                f"{', '.join(VALID_EXTENSIONS[asset_type])})"
            )
        if not data:
            raise ValueError(f"Empty file for {asset_type}")
        if len(data) > MAX_BYTES[asset_type]:
            raise ValueError(
                f"File too large for {asset_type}: {len(data)} bytes (max {MAX_BYTES[asset_type]})"
            )
        asset = Asset(
            type=asset_type,
            name=name,
            description=description,
            tags=tags or [],
            role=role,
            meta={
                "size_bytes": len(data),
                "mime": MIME_BY_EXT[ext],
                "ext": ext,
            },
        )
        sub_dir = ASSETS_ROOT / asset_type
        sub_dir.mkdir(parents=True, exist_ok=True)
        file_path = sub_dir / f"{asset.id}.{ext}"
        file_path.write_bytes(data)
        asset.file_path = f"{asset_type}/{asset.id}.{ext}"
        try:
            return await self.repo.create(asset)
        except Exception:
            file_path.unlink(missing_ok=True)
            raise

    async def update_asset(self, asset_id: str, updates: dict) -> Asset | None:
        return await self.repo.update(asset_id, updates)

    async def delete_asset(self, asset_id: str) -> bool:
        asset = await self.get(asset_id)
        if not asset:
            return False
        if not await self.repo.delete(asset_id):
            return False
        if asset.file_path:
            self.absolute_path(asset.file_path).unlink(missing_ok=True)
        return True
