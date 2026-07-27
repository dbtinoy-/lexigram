from shorts_creator.controllers.api.render_api import RenderApiController
from shorts_creator.services.core import AppConfig


class FakeHistoryService:
    def __init__(self, runs=None):
        self._runs = runs or {}

    async def get_run(self, run_id):
        return self._runs.get(run_id)


class FakeScriptService:
    last_script = None


class FakeRunService:
    async def get(self, run_id):
        return None


class FakeProjectService:
    async def get_script(self, project_id, idea_id):
        return None


def make_controller(history=None):
    return RenderApiController(
        scripts=FakeScriptService(),
        ideas=None,
        history=history or FakeHistoryService(),
        project_service=FakeProjectService(),
        task_manager=None,
        config=AppConfig(),
        runs=FakeRunService(),
    )


class TestVideoEndpointErrors:
    async def test_preview_unknown_run_returns_404_not_error(self):
        controller = make_controller()
        result = await controller.preview_video(request=None, run_id="missing")
        assert result.status_code == 404

    async def test_download_unknown_run_returns_404_not_error(self):
        controller = make_controller()
        result = await controller.download_video(request=None, run_id="missing")
        assert result.status_code == 404

    async def test_preview_missing_file_returns_404_not_error(self):
        history = FakeHistoryService({"r1": {"output": "/nonexistent/video.mp4"}})
        controller = make_controller(history)
        result = await controller.preview_video(request=None, run_id="r1")
        assert result.status_code == 404

    async def test_poster_unknown_run_returns_404(self):
        controller = make_controller()
        result = await controller.video_poster(request=None, run_id="missing")
        assert result.status_code == 404

    async def test_poster_missing_file_returns_404(self):
        history = FakeHistoryService({"r1": {"output": "/nonexistent/video.mp4"}})
        controller = make_controller(history)
        result = await controller.video_poster(request=None, run_id="r1")
        assert result.status_code == 404

    async def test_poster_missing_jpg_returns_404(self, tmp_path):
        video = tmp_path / "video.mp4"
        video.write_bytes(b"video")
        history = FakeHistoryService({"r1": {"output": str(video)}})
        controller = make_controller(history)
        result = await controller.video_poster(request=None, run_id="r1")
        assert result.status_code == 404

    async def test_poster_serves_jpg(self, tmp_path):
        video = tmp_path / "video.mp4"
        video.write_bytes(b"video")
        poster = tmp_path / "video.jpg"
        poster.write_bytes(b"poster")
        history = FakeHistoryService({"r1": {"output": str(video)}})
        controller = make_controller(history)
        result = await controller.video_poster(request=None, run_id="r1")
        assert result.status_code == 200
