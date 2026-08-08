from shorts_creator.controllers.api.render_api import RenderApiController
from shorts_creator.services.core import AppConfig


class _Request:
    def __init__(self, qp):
        self.query_params = qp


class FakeHistoryService:
    def __init__(self, runs=None):
        self._runs = runs or []

    async def get_recent(self, limit=100):
        return self._runs

    async def get_run(self, run_id):
        return None


class FakeScriptService:
    last_script = None

    async def generate_seo(self, script):
        return {"title": "SEO Title", "description": "d", "tags": ["t"], "facebook_caption": "f"}


class _FakeDbRun:
    def __init__(self, project_id, selected_idea_id=None):
        self.project_id = project_id
        self.selected_idea_id = selected_idea_id


class FakeRunService:
    def __init__(self, project_by_run=None):
        self._project_by_run = project_by_run or {}

    async def get(self, run_id):
        entry = self._project_by_run.get(run_id)
        if not entry:
            return None
        return _FakeDbRun(entry[0], entry[1])


class FakeProjectService:
    def __init__(self):
        self.saved = []
        self.script = {
            "title": "S",
            "sections": [{"name": "hook", "text": "Hi", "duration_seconds": 2.0}],
            "total_duration": 2.0,
            "word_count": 3,
            "pacing_wps": 1.5,
            "emotional_arc": None,
            "metadata": {},
        }

    async def get_script(self, project_id, idea_id):
        if project_id == "proj-9" and idea_id == "idea-1":
            return self.script
        return None

    async def save_script(self, project_id, idea_id, script):
        self.script = script
        self.saved.append((project_id, idea_id, script))

    async def list_recent(self, limit=10):
        return []


def make_controller(history=None, runs=None):
    controller = RenderApiController(
        scripts=FakeScriptService(),
        ideas=None,
        history=history or FakeHistoryService(),
        project_service=FakeProjectService(),
        task_manager=None,
        config=AppConfig(),
        runs=runs or FakeRunService(),
    )
    return controller


class TestGenerateSeoPersists:
    async def test_targeted_generation_persists_seo_to_idea(self):
        controller = make_controller()
        await controller.generate_seo(
            request=_Request({"project_id": "proj-9", "idea_id": "idea-1"})
        )
        assert controller.project_service.saved
        project_id, idea_id, script = controller.project_service.saved[0]
        assert (project_id, idea_id) == ("proj-9", "idea-1")
        assert script["metadata"]["seo"]["title"] == "SEO Title"

    async def test_targeted_generation_returns_videos_fragment(self):
        controller = make_controller()
        html = await controller.generate_seo(
            request=_Request({"project_id": "proj-9", "idea_id": "idea-1"})
        )
        assert "videos-content" in str(html)

    async def test_card_generation_returns_single_card_for_latest_render(self, tmp_path):
        video = tmp_path / "v.mp4"
        video.write_bytes(b"v")
        history = FakeHistoryService(
            [
                {
                    "status": "completed",
                    "idea": "S",
                    "run_id": "r1",
                    "duration_s": 2.0,
                    "output": str(video),
                }
            ]
        )
        runs = FakeRunService({"r1": ("proj-9", "idea-1")})
        controller = make_controller(history=history, runs=runs)
        html = str(
            await controller.generate_seo(
                request=_Request({"project_id": "proj-9", "idea_id": "idea-1", "card": "1"})
            )
        )
        assert "SEO &amp; Social Distribution" in html or "SEO & Social Distribution" in html
        assert 'hx-target="#latest-render"' in html
        assert "videos-content" not in html
        assert 'href="/api/videos/download/r1"' in html

    async def test_targeted_generation_missing_script_returns_error(self):
        controller = make_controller()
        html = await controller.generate_seo(
            request=_Request({"project_id": "proj-x", "idea_id": "idea-z"})
        )
        assert "No script" in str(html)
        assert not controller.project_service.saved
