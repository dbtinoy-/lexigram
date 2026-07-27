from shorts_creator.models.asset import Asset
from shorts_creator.models.asset_bundle import AssetBundle
from shorts_creator.models.project import Project
from shorts_creator.services.asset_resolver import AssetResolver


class _FakeRepo:
    def __init__(self, assets=None):
        self.assets = assets or {}

    async def get(self, asset_id):
        return self.assets.get(asset_id)


class TestAssetResolver:
    def _resolver(self, assets):
        return AssetResolver(_FakeRepo(assets))

    async def test_project_ref_wins(self):
        font = Asset(type="font", name="Inter", file_path="font/1.ttf")
        resolver = self._resolver({"f1": font})
        project = Project(topic="t", asset_font_id="f1")
        bundle = await resolver.resolve(project, {"asset_default_font_id": "other"})
        assert bundle.font_path == "font/1.ttf"

    async def test_global_default_fills_when_project_unset(self):
        music = Asset(type="music", name="Lo-fi", file_path="music/1.mp3")
        resolver = self._resolver({"m1": music})
        bundle = await resolver.resolve(Project(topic="t"), {"asset_default_music_id": "m1"})
        assert bundle.music_path == "music/1.mp3"

    async def test_missing_asset_falls_back_to_none(self):
        resolver = self._resolver({})
        project = Project(topic="t", asset_font_id="missing")
        bundle = await resolver.resolve(project, {"asset_default_font_id": "also-missing"})
        assert bundle.font_path is None

    async def test_defaults_are_all_none_when_nothing_set(self):
        resolver = self._resolver({})
        bundle = await resolver.resolve(Project(topic="t"), {})
        assert bundle == AssetBundle()
        assert bundle.outro_clip_path is None

    async def test_bg_and_outro_roles_resolve(self):
        outro = Asset(type="clip", name="End", role="outro", file_path="clip/outro.mp4")
        bg = Asset(type="clip", name="Forest", role="background", file_path="clip/bg.mp4")
        resolver = self._resolver({"o1": outro, "b1": bg})
        bundle = await resolver.resolve(
            Project(topic="t", asset_outro_clip_id="o1", asset_bg_clip_id="b1"), {}
        )
        assert bundle.outro_clip_path == "clip/outro.mp4"
        assert bundle.bg_clip_path == "clip/bg.mp4"

    async def test_empty_project_ref_falls_through_to_global(self):
        music = Asset(type="music", name="Lo-fi", file_path="music/1.mp3")
        resolver = self._resolver({"m1": music})
        bundle = await resolver.resolve(
            Project(topic="t", asset_music_id=""), {"asset_default_music_id": "m1"}
        )
        assert bundle.music_path == "music/1.mp3"

    async def test_resolve_without_project_uses_global(self):
        font = Asset(type="font", name="Inter", file_path="font/1.ttf")
        resolver = self._resolver({"f1": font})
        bundle = await resolver.resolve(None, {"asset_default_font_id": "f1"})
        assert bundle.font_path == "font/1.ttf"

    async def test_media_url_watermark_overrides_watermark_path(self):
        resolver = self._resolver({})
        bundle = await resolver.resolve(
            None, {"media_url_watermark": "https://cdn.example/logo.png"}
        )
        assert bundle.watermark_path == "https://cdn.example/logo.png"

    async def test_watermark_url_wins_over_selected_asset(self):
        watermark = Asset(type="image", name="Logo", file_path="image/logo.png")
        resolver = self._resolver({"w1": watermark})
        bundle = await resolver.resolve(
            None,
            {
                "asset_default_watermark_id": "w1",
                "media_url_watermark": "https://cdn.example/logo.png",
            },
        )
        assert bundle.watermark_path == "https://cdn.example/logo.png"
