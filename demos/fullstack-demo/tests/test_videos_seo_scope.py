import re

from shorts_creator.controllers.videos import VideosController


class FakeHistoryService:
    def __init__(self, runs):
        self._runs = runs

    async def get_recent(self, limit=100):
        return self._runs


class FakeScriptService:
    last_script = None


class _FakeDbRun:
    def __init__(self, project_id, selected_idea_id=None):
        self.project_id = project_id
        self.selected_idea_id = selected_idea_id


class FakeRunService:
    def __init__(self, runs=None):
        self._runs = runs or {}

    async def get(self, run_id):
        return self._runs.get(run_id)


class FakeProjectService:
    def __init__(self, scripts=None, project=None):
        self._scripts = scripts or {}
        self._project = project

    async def get(self, project_id):
        return self._project

    async def get_script(self, project_id, idea_id):
        return self._scripts.get(f"{project_id}:{idea_id}")


class FakeProject:
    id = "proj-9"
    title = "My Project"
    topic = ""
    format = ""
    caption_style = ""
    focus = ""
    created_at = None
    idea_json = None


COMPLETED_RUN = {"status": "completed", "idea": "Test Idea", "run_id": "r1", "duration_s": 30}

SCRIPT_WITH_SEO = {
    "title": "Test Script",
    "sections": [{"name": "hook", "text": "Hi", "duration_seconds": 2.0}],
    "total_duration": 2.0,
    "metadata": {
        "seo": {
            "title": "SEO Title",
            "description": "desc",
            "tags": ["t"],
            "facebook_caption": "cap",
        }
    },
}

SCRIPT_WITHOUT_SEO = {**SCRIPT_WITH_SEO, "metadata": {}}


def make_controller(runs, db_runs=None, scripts=None):
    return VideosController(
        history=FakeHistoryService(runs),
        scripts=FakeScriptService(),
        runs=FakeRunService(db_runs),
        projects=FakeProjectService(scripts, FakeProject()),
    )


async def videos_html(controller) -> str:
    return str(await controller.project_videos(request=None, id="proj-9"))


class TestVideosTwoGrids:
    async def test_completed_runs_split_across_two_grids(self):
        controller = make_controller(
            [COMPLETED_RUN, {**COMPLETED_RUN, "run_id": "r2"}],
            db_runs={"r1": _FakeDbRun("proj-9", "idea-1"), "r2": _FakeDbRun("proj-9", "idea-2")},
            scripts={"proj-9:idea-1": SCRIPT_WITH_SEO},
        )
        html = await videos_html(controller)
        assert "Ready for Distribution" in html
        assert "Awaiting SEO" in html

    async def test_item_without_seo_shows_generate_button(self):
        controller = make_controller(
            [COMPLETED_RUN],
            db_runs={"r1": _FakeDbRun("proj-9", "idea-1")},
            scripts={"proj-9:idea-1": SCRIPT_WITHOUT_SEO},
        )
        html = await videos_html(controller)
        assert "/api/render/generate-seo?project_id=proj-9" in html
        assert "No SEO metadata" in html

    async def test_item_with_seo_shows_panel(self):
        controller = make_controller(
            [COMPLETED_RUN],
            db_runs={"r1": _FakeDbRun("proj-9", "idea-1")},
            scripts={"proj-9:idea-1": SCRIPT_WITH_SEO},
        )
        html = await videos_html(controller)
        assert "SEO &amp; Social Distribution" in html or "SEO & Social Distribution" in html
        assert "No SEO metadata" not in html

    async def test_item_with_seo_fields_are_editable(self):
        controller = make_controller(
            [COMPLETED_RUN],
            db_runs={"r1": _FakeDbRun("proj-9", "idea-1")},
            scripts={"proj-9:idea-1": SCRIPT_WITH_SEO},
        )
        html = await videos_html(controller)
        assert 'id="seo-youtube_title-idea-1"' in html
        assert 'id="seo-youtube_description-idea-1"' in html
        assert 'id="seo-youtube_tags-idea-1"' in html
        assert 'id="seo-facebook_caption-idea-1"' in html
        assert "cap" in html.split('id="seo-facebook_caption-idea-1"')[1].split("</textarea>")[0]
        assert html.count('hx-post="/api/scripts/seo/update"') == 4

    async def test_seo_fields_have_no_rounded_container(self):
        controller = make_controller(
            [COMPLETED_RUN],
            db_runs={"r1": _FakeDbRun("proj-9", "idea-1")},
            scripts={"proj-9:idea-1": SCRIPT_WITH_SEO},
        )
        html = await videos_html(controller)
        assert "mb-3 p-3.5 bg-card/90 rounded-xl" not in html

    async def test_legacy_run_without_idea_has_no_generate_button(self):
        controller = make_controller([COMPLETED_RUN], db_runs={"r1": _FakeDbRun("proj-9")})
        html = await videos_html(controller)
        assert "/api/render/generate-seo" not in html
        assert "not linked to a script" in html

    async def test_regenerate_button_below_fields(self):
        controller = make_controller(
            [COMPLETED_RUN],
            db_runs={"r1": _FakeDbRun("proj-9", "idea-1")},
            scripts={"proj-9:idea-1": SCRIPT_WITH_SEO},
        )
        html = await videos_html(controller)
        regenerate = html.index("Regenerate SEO")
        last_field = html.index('id="seo-facebook_caption-idea-1"')
        assert last_field < regenerate
        assert " mt-3" in html
        assert (
            html.count(
                "M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"
            )
            == 1
        )

    async def test_save_buttons_show_save_icon_only(self):
        controller = make_controller(
            [COMPLETED_RUN],
            db_runs={"r1": _FakeDbRun("proj-9", "idea-1")},
            scripts={"proj-9:idea-1": SCRIPT_WITH_SEO},
        )
        html = await videos_html(controller)
        assert html.count("M20 6L9 17l-5-5") == 4
        assert html.count('title="Save"') == 4
        assert html.count("M19 21H5a2") == 0

    async def test_grid_empty_states(self):
        controller = make_controller(
            [COMPLETED_RUN],
            db_runs={"r1": _FakeDbRun("proj-9", "idea-1")},
            scripts={"proj-9:idea-1": SCRIPT_WITH_SEO},
        )
        html = await videos_html(controller)
        assert "All videos have SEO metadata" in html


class TestVersionGrouping:
    async def test_same_idea_runs_grouped_into_single_card_with_chips(self):
        controller = make_controller(
            [
                {
                    **COMPLETED_RUN,
                    "run_id": "r2",
                    "duration_s": 30,
                    "created_at": "2026-07-31T11:00:00",
                },
                {
                    **COMPLETED_RUN,
                    "run_id": "r1",
                    "duration_s": 12,
                    "created_at": "2026-07-31T10:00:00",
                },
            ],
            db_runs={"r1": _FakeDbRun("proj-9", "idea-1"), "r2": _FakeDbRun("proj-9", "idea-1")},
            scripts={"proj-9:idea-1": SCRIPT_WITHOUT_SEO},
        )
        html = await videos_html(controller)
        assert html.count(">Test Idea</h3>") == 1
        assert "Ver:" in html
        assert 'hx-get="/projects/proj-9/videos/version/r1"' in html
        assert 'hx-get="/projects/proj-9/videos/version/r2"' in html
        assert "12.0s" not in html
        assert "30.0s" in html

    async def test_version_swap_returns_card_for_that_version(self):
        controller = make_controller(
            [
                {
                    **COMPLETED_RUN,
                    "run_id": "r2",
                    "duration_s": 30,
                    "created_at": "2026-07-31T11:00:00",
                },
                {
                    **COMPLETED_RUN,
                    "run_id": "r1",
                    "duration_s": 12,
                    "created_at": "2026-07-31T10:00:00",
                },
            ],
            db_runs={"r1": _FakeDbRun("proj-9", "idea-1"), "r2": _FakeDbRun("proj-9", "idea-1")},
            scripts={"proj-9:idea-1": SCRIPT_WITHOUT_SEO},
        )
        html = str(await controller.version_card(request=None, id="proj-9", run_id="r1"))
        assert "12.0s" in html
        assert "Ver:" in html

    async def test_single_version_has_no_chips(self):
        controller = make_controller(
            [COMPLETED_RUN],
            db_runs={"r1": _FakeDbRun("proj-9", "idea-1")},
            scripts={"proj-9:idea-1": SCRIPT_WITHOUT_SEO},
        )
        html = await videos_html(controller)
        assert "Ver:" not in html

    async def test_different_ideas_stay_separate_cards(self):
        controller = make_controller(
            [
                {**COMPLETED_RUN, "run_id": "r1"},
                {**COMPLETED_RUN, "run_id": "r2", "idea": "Other Idea"},
            ],
            db_runs={"r1": _FakeDbRun("proj-9", "idea-1"), "r2": _FakeDbRun("proj-9", "idea-2")},
            scripts={"proj-9:idea-1": SCRIPT_WITHOUT_SEO, "proj-9:idea-2": SCRIPT_WITHOUT_SEO},
        )
        html = await videos_html(controller)
        assert "Ver:" not in html
        assert "Test Idea" in html
        assert "Other Idea" in html


class TestVersionChipsCap:
    def runs(self, count):
        return [
            {
                **COMPLETED_RUN,
                "run_id": f"r{i}",
                "duration_s": i,
                "created_at": f"2026-07-31T{10 + i:02d}:00:00",
            }
            for i in range(1, count + 1)
        ]

    def controller(self, count, db=None):
        return make_controller(
            list(reversed(self.runs(count))),
            db_runs=db or {f"r{i}": _FakeDbRun("proj-9", "idea-1") for i in range(1, count + 1)},
            scripts={"proj-9:idea-1": SCRIPT_WITHOUT_SEO},
        )

    async def test_many_versions_truncated_with_ellipsis(self):
        html = await videos_html(self.controller(8))
        chip_ids = re.findall(r'hx-get="/projects/proj-9/videos/version/(r\d)"', html)
        assert chip_ids == ["r1", "r2", "r3", "r6", "r7", "r8"]
        strip = re.search(r"Ver:</span>(.*?)</div>", html, re.DOTALL).group(1)
        assert "\u2026" in strip

    async def test_six_versions_shown_without_ellipsis(self):
        html = await videos_html(self.controller(6))
        chip_ids = re.findall(r'hx-get="/projects/proj-9/videos/version/(r\d)"', html)
        assert chip_ids == ["r1", "r2", "r3", "r4", "r5", "r6"]
        strip = re.search(r"Ver:</span>(.*?)</div>", html, re.DOTALL).group(1)
        assert "\u2026" not in strip

    async def test_active_middle_version_kept_visible(self):
        html = str(await self.controller(8).version_card(request=None, id="proj-9", run_id="r5"))
        chip_ids = re.findall(r'hx-get="/projects/proj-9/videos/version/(r\d)"', html)
        assert chip_ids == ["r1", "r2", "r3", "r5", "r6", "r7", "r8"]
        assert 'bg-primary text-primary-foreground border-primary">5</button>' in html


class TestVideoPlayer:
    async def test_player_is_portrait_with_native_controls(self):
        controller = make_controller(
            [COMPLETED_RUN], db_runs={"r1": _FakeDbRun("proj-9", "idea-1")}
        )
        html = await videos_html(controller)
        assert "aspect-[9/16]" in html
        assert 'controls=""' in html
        assert 'preload="metadata"' in html

    async def test_legacy_run_with_zero_duration_probes_video_file(self, monkeypatch):
        from shorts_creator.controllers import videos as videos_mod

        run = {**COMPLETED_RUN, "duration_s": 0, "output": "/some/video.mp4"}
        monkeypatch.setattr(videos_mod, "probe_duration", lambda path: 42.3)
        controller = make_controller([run], db_runs={"r1": _FakeDbRun("proj-9")})
        html = await videos_html(controller)
        assert "\u23f1 42.3s" in html
        assert "42s" in html

    async def test_missing_video_file_keeps_dash_duration(self, monkeypatch):
        from shorts_creator.controllers import videos as videos_mod

        run = {**COMPLETED_RUN, "duration_s": 0, "output": "/some/video.mp4"}
        monkeypatch.setattr(videos_mod, "probe_duration", lambda path: 0.0)
        controller = make_controller([run], db_runs={"r1": _FakeDbRun("proj-9")})
        html = await videos_html(controller)
        assert "\u23f1 \u2014" in html
