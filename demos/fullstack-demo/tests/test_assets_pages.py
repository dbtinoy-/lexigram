from unittest.mock import MagicMock

from shorts_creator.controllers.assets import AssetsController
from shorts_creator.models.asset import Asset
from shorts_creator.models.run import Run, RunStatus


class _FakeService:
    def __init__(self, assets=None):
        self.assets = assets or [
            Asset(type="music", name="Lo-fi", file_path="music/1.mp3"),
            Asset(type="clip", name="Forest", role="background", file_path="clip/2.mp4"),
            Asset(type="font", name="Inter", file_path="font/3.ttf"),
        ]

    async def get(self, asset_id):
        return next((a for a in self.assets if a.id == asset_id), None)

    async def list_all(self):
        return self.assets

    async def list_by_type(self, asset_type, role=None):
        return [a for a in self.assets if a.type == asset_type]


class _FakeLayout:
    def render(self, content="", title="", request=None):
        return f"<html>{title}|{content}</html>"


class TestAssetsPages:
    def _controller(self, service=None):
        c = AssetsController(service or _FakeService())
        c.layout = _FakeLayout()
        return c

    async def test_library_page_lists_assets(self):
        c = self._controller()
        req = MagicMock()
        req.query_params = {}
        resp = await c.library(request=req)
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "Asset Library" in body
        assert "Lo-fi" in body
        assert "Forest" in body
        assert "Inter" in body

    async def test_library_page_filters_by_type(self):
        c = self._controller()
        req = MagicMock()
        req.query_params = {"type": "music"}
        resp = await c.library(request=req)
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "Lo-fi" in body
        assert "Forest" not in body

    async def test_upload_page_shows_role_select_for_clips(self):
        c = self._controller()
        req = MagicMock()
        req.query_params = {"type": "clip"}
        resp = await c.new_asset(request=req)
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "role" in body
        assert "outro" in body

    async def test_upload_page_hides_role_select_for_music(self):
        c = self._controller()
        req = MagicMock()
        req.query_params = {"type": "music"}
        resp = await c.new_asset(request=req)
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert 'name="role"' not in body

    async def test_edit_page_renders_current_values(self):
        service = _FakeService()
        c = self._controller(service)
        resp = await c.edit(request=None, id=service.assets[0].id)
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "Edit Asset" in body
        assert "Lo-fi" in body

    async def test_edit_page_role_placeholder_for_roleless_clip(self):
        service = _FakeService(
            assets=[
                Asset(type="clip", name="No Role", file_path="clip/1.mp4"),
            ]
        )
        c = self._controller(service)
        resp = await c.edit(request=None, id=service.assets[0].id)
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert '<option value="" selected>None (built-in)</option>' in body
        assert '<option value="background" selected>' not in body

    async def test_edit_page_preselects_stored_role(self):
        service = _FakeService()
        c = self._controller(service)
        resp = await c.edit(request=None, id=service.assets[1].id)
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert '<option value="background" selected>' in body

    async def test_edit_page_404_for_unknown_asset(self):
        c = self._controller()
        resp = await c.edit(request=None, id="does-not-exist")
        assert resp.status_code == 404


class MockRequest:
    def __init__(self, query_params):
        self.query_params = query_params


class TestAssetsTaskFixes:
    def _controller(self, service=None):
        c = AssetsController(service or _FakeService())
        c.layout = _FakeLayout()
        return c

    async def test_upload_link_carries_active_filter(self):
        c = self._controller()
        req = MockRequest({"type": "font"})
        resp = await c.library(request=req)
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "/assets/new?type=font" in body

    async def test_upload_link_without_filter_stays_clean(self):
        c = self._controller()
        resp = await c.library(request=MockRequest({}))
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert 'href="/assets/new"' in body
        assert "/assets/new?" not in body

    async def test_image_and_watermark_cards_render_preview(self):
        service = _FakeService(
            assets=[
                Asset(type="image", name="Hero", file_path="image/1.png"),
                Asset(type="watermark", name="Logo", file_path="watermark/2.png"),
            ]
        )
        c = self._controller(service)
        resp = await c.library(request=MockRequest({}))
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert f"/api/assets/{service.assets[0].id}/file" in body
        assert f"/api/assets/{service.assets[1].id}/file" in body

    async def test_upload_heading_uses_singular_labels(self):
        c = self._controller()
        for asset_type, label in [
            ("font", "Upload Font Asset"),
            ("clip", "Upload Clip Asset"),
            ("music", "Upload Music Asset"),
            ("weird", "Upload Asset"),
        ]:
            resp = await c.new_asset(request=MockRequest({"type": asset_type}))
            body = resp.body if hasattr(resp, "body") else str(resp)
            assert label in body
            if asset_type == "weird":
                assert "Upload Asset Asset" not in body


class _FakeRuns:
    def __init__(self, runs=None):
        self.runs = runs or []

    async def list_status(self, status, limit=10_000):
        return [r for r in self.runs if r.status == status]


class _FakeProjects:
    def __init__(self, projects=None):
        self.projects = projects or {}

    async def get(self, project_id):
        return self.projects.get(project_id)


class _FakeProject:
    def __init__(self, title):
        self.title = title


class TestGeneratedVideosTab:
    def _controller(self, runs=None, projects=None):
        c = AssetsController(
            _FakeService(), runs=runs or _FakeRuns(), projects=projects or _FakeProjects()
        )
        c.layout = _FakeLayout()
        return c

    async def test_top_level_tabs_present(self):
        c = self._controller()
        resp = await c.library(request=MockRequest({}))
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert 'href="/assets" hx-get="/assets"' in body
        assert 'href="/assets?tab=generated"' in body

    async def test_generated_tab_renders_all_project_videos(self, tmp_path):
        v1 = tmp_path / "x.mp4"
        v2 = tmp_path / "y.mp4"
        v1.write_bytes(b"x")
        v2.write_bytes(b"y")
        run1 = Run(
            project_id="p1",
            title="Morning Routine",
            status=RunStatus.COMPLETED,
            output_path=str(v1),
            duration_s=34.5,
        )
        run2 = Run(
            project_id="p2",
            title="",
            status=RunStatus.COMPLETED,
            output_path=str(v2),
            duration_s=12.0,
        )
        c = self._controller(
            runs=_FakeRuns([run1, run2]),
            projects=_FakeProjects({"p1": _FakeProject("Alpha"), "p2": _FakeProject("Beta")}),
        )
        resp = await c.library(request=MockRequest({"tab": "generated"}))
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "Morning Routine" in body
        assert "Alpha" in body
        assert "Beta" in body
        assert f"/api/videos/preview/{run1.id}" in body
        assert f"/api/videos/download/{run1.id}" in body
        assert f"/api/videos/preview/{run2.id}" in body

    async def test_generated_tab_excludes_non_completed(self, tmp_path):
        v = tmp_path / "z.mp4"
        v.write_bytes(b"z")
        draft = Run(project_id="p1", title="Draft", status=RunStatus.DRAFT, output_path=str(v))
        c = self._controller(
            runs=_FakeRuns([draft]), projects=_FakeProjects({"p1": _FakeProject("Alpha")})
        )
        resp = await c.library(request=MockRequest({"tab": "generated"}))
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "No generated videos yet" in body

    async def test_generated_tab_hides_upload_button(self):
        c = self._controller()
        resp = await c.library(request=MockRequest({"tab": "generated"}))
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert " Upload" not in body
        resp2 = await c.library(request=MockRequest({}))
        body2 = resp2.body if hasattr(resp2, "body") else str(resp2)
        assert " Upload" in body2
