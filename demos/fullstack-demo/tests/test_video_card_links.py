from shorts_creator.controllers.videos import VideoCard, VideosController, _GroupCard


class TestVideoCardProjectLink:
    def test_links_to_run_when_project_id_known(self):
        html = VideoCard({"run_id": "r1", "idea": "Test", "duration_s": 10}, project_id="p1")
        assert "/projects/p1/runs/r1" in html

    def test_omits_link_when_project_unresolvable(self):
        html = VideoCard({"run_id": "r2", "idea": "Test", "duration_s": 10}, project_id=None)
        assert "/projects/" not in html

    def test_buttons_are_stacked_vertically(self):
        html = VideoCard({"run_id": "r1", "idea": "Test", "duration_s": 10}, project_id="p1")
        assert 'class="mt-3 flex flex-col gap-1.5"' in html

    def test_download_button_uses_cloud_icon(self):
        html = VideoCard({"run_id": "r1", "idea": "Test", "duration_s": 10}, project_id="p1")
        assert "M4 14.899A7" in html

    def test_includes_open_project_button(self):
        html = VideoCard({"run_id": "r1", "idea": "Test", "duration_s": 10}, project_id="p1")
        assert 'href="/projects/p1"' in html

    def test_omits_open_script_when_idea_index_unknown(self):
        html = VideoCard(
            {"run_id": "r1", "idea": "Test", "duration_s": 10}, project_id="p1", idea_id="idea-1"
        )
        assert "/projects/p1/scripts" not in html

    def test_open_script_link_uses_idea_index(self):
        group = {
            "key": "Test",
            "title": "Test",
            "project_id": "p1",
            "idea_id": "idea-1",
            "idea_index": 0,
            "seo": None,
            "versions": [{"run_id": "r1", "idea": "Test", "duration_s": 10}],
            "active_run_id": "r1",
        }
        html = _GroupCard(group)
        assert 'href="/projects/p1/scripts?idea_index=0"' in html
        assert "Open Script" in html
        assert "View Run" in html

    def test_video_sets_poster_when_jpg_exists(self, tmp_path):
        video = tmp_path / "v.mp4"
        video.write_bytes(b"v")
        poster = tmp_path / "v.jpg"
        poster.write_bytes(b"p")
        html = VideoCard({"run_id": "r1", "idea": "Test", "duration_s": 10, "output": str(video)})
        assert 'poster="/api/videos/poster/r1"' in html

    def test_video_always_requests_poster_and_api_extracts_lazily(self, tmp_path):
        video = tmp_path / "v.mp4"
        video.write_bytes(b"v")
        html = VideoCard({"run_id": "r1", "idea": "Test", "duration_s": 10, "output": str(video)})
        assert 'poster="/api/videos/poster/r1"' in html


class FakeHistoryService:
    def __init__(self, runs):
        self._runs = runs

    async def get_recent(self, limit=100):
        return self._runs


class FakeScriptService:
    last_script = None


class _FakeDbRun:
    def __init__(self, project_id):
        self.project_id = project_id


class FakeRunService:
    def __init__(self, project_by_run):
        self._project_by_run = project_by_run

    async def get(self, run_id):
        pid = self._project_by_run.get(run_id)
        return _FakeDbRun(pid) if pid else None


class FakeProjectService:
    def __init__(self, projects=None):
        self._projects = projects or {}

    async def get(self, project_id):
        return self._projects.get(project_id)


class _FakeProject:
    def __init__(self, id):
        self.id = id


class TestVideosListResolvesProjectLinks:
    async def test_grid_links_completed_video_to_its_project(self):
        controller = VideosController(
            history=FakeHistoryService(
                [{"status": "completed", "idea": "Test", "run_id": "r1", "duration_s": 10}]
            ),
            scripts=FakeScriptService(),
            runs=FakeRunService({"r1": "proj-9"}),
            projects=FakeProjectService({"proj-9": _FakeProject(id="proj-9")}),
        )
        html = str(await controller.project_videos(request=None, id="proj-9"))
        assert "/projects/proj-9/runs/r1" in html


class TestProjectVideosTab:
    async def test_project_videos_404s_unknown_project(self):
        controller = VideosController(
            history=FakeHistoryService([]),
            scripts=FakeScriptService(),
            runs=FakeRunService({}),
            projects=FakeProjectService(),
        )
        result = await controller.project_videos(request=None, id="missing")
        assert getattr(result, "status_code", None) == 404

    async def test_project_videos_shows_tabs_and_scopes_to_project(self):
        controller = VideosController(
            history=FakeHistoryService(
                [
                    {"status": "completed", "idea": "Mine", "run_id": "r1", "duration_s": 10},
                    {"status": "completed", "idea": "Other", "run_id": "r2", "duration_s": 10},
                ]
            ),
            scripts=FakeScriptService(),
            runs=FakeRunService({"r1": "proj-a", "r2": "proj-b"}),
            projects=FakeProjectService({"proj-a": _FakeProject(id="proj-a")}),
        )
        html = str(await controller.project_videos(request=None, id="proj-a"))
        assert "Project Videos" in html
        assert 'href="/projects/proj-a/videos"' in html
        assert "bg-primary text-primary-foreground border-primary" in html
        assert "Mine" in html
        assert "Other" not in html


class TestVideoCardTooltip:
    def test_tooltip_shows_filename_not_fs_path(self, tmp_path):
        video = tmp_path / "renders" / "my_video.mp4"
        video.parent.mkdir()
        video.write_bytes(b"v")
        html = VideoCard(
            {"run_id": "r1", "idea": "Test", "duration_s": 10, "output": str(video)},
            project_id="p1",
        )
        assert f'title="{video.name}"' in html
        assert str(video.parent) not in html
