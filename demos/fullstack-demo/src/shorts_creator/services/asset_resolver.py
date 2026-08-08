from shorts_creator.models.asset_bundle import AssetBundle
from shorts_creator.models.project import Project


class AssetResolver:
    """Resolve per-project asset refs -> global defaults -> built-in (None).

    Returns an AssetBundle of file paths relative to ASSETS_ROOT (e.g.
    "music/<id>.mp3"); callers must prepend ASSETS_ROOT to build absolute
    paths for the pipeline. Media URL overrides (media_url_*) take priority
    and pass the URL through as-is so callers can download it.
    """

    REFS = (
        ("asset_music_id", "asset_default_music_id", "music_path", "media_url_music"),
        ("asset_font_id", "asset_default_font_id", "font_path", None),
        (
            "asset_watermark_id",
            "asset_default_watermark_id",
            "watermark_path",
            "media_url_watermark",
        ),
        ("asset_bg_clip_id", "asset_default_bg_clip_id", "bg_clip_path", "media_url_bg_clip"),
        (
            "asset_outro_clip_id",
            "asset_default_outro_clip_id",
            "outro_clip_path",
            "media_url_outro",
        ),
    )

    def __init__(self, repo):
        self.repo = repo

    async def resolve(self, project: Project | None, overrides: dict[str, str]) -> AssetBundle:
        values: dict[str, str | None] = {}
        for project_key, override_key, bundle_key, url_key in self.REFS:
            asset_id = None
            if project is not None:
                asset_id = getattr(project, project_key, None)
            if not asset_id:
                asset_id = overrides.get(override_key) or None
            path = None
            if url_key and overrides.get(url_key):
                path = overrides[url_key]
            elif asset_id:
                asset = await self.repo.get(asset_id)
                if asset and asset.file_path:
                    path = asset.file_path
            values[bundle_key] = path
        return AssetBundle(**values)
