import json

from shorts_creator.contracts.issues import ContractIssue, Severity
from shorts_creator.controllers.projects import ProjectsController, _project_dashboard, _ProjectCard
from shorts_creator.models.project import Project
from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProfileSource,
    ResolvedSetting,
)
from shorts_creator.models.run import Run, RunStatus
from shorts_creator.services.project_state import derive_project_state


def make_project(id="p1", idea_json=None):
    return Project(id=id, topic="self_improvement", idea_json=idea_json)


def idea_dict(i, script=False, title=None, seo=None):
    d = {"id": f"idea{i}", "title": title or f"Idea {i}", "core_message": f"Msg {i}"}
    if script:
        d["script_json"] = json.dumps(
            {
                "title": "S",
                "sections": [],
                "total_duration": 30,
                "word_count": 120,
                "metadata": {"seo": seo} if seo else None,
            }
        )
    return d


def _setting(value, source: ProfileSource) -> ResolvedSetting:
    return ResolvedSetting(
        value=value, source=source, is_overridden=source is ProfileSource.PROJECT
    )


def make_profile(duration=30.0):
    return EffectiveProjectProfile(
        duration_seconds=_setting(duration, ProfileSource.PROJECT),
        caption_style=_setting("highlight", ProfileSource.GLOBAL),
        format_name=_setting("narrated", ProfileSource.GLOBAL),
        topic=_setting("self_improvement", ProfileSource.PROJECT),
        reel_width=_setting(1080, ProfileSource.BUILT_IN),
        reel_height=_setting(1920, ProfileSource.BUILT_IN),
    )


class TestDashboardStates:
    async def test_empty_project_shows_start_creating_cta(self):
        html = _project_dashboard(make_project(), derive_project_state(make_project(), []))
        assert "Start Creating" in html
        assert "Pipeline Progress" not in html

    async def test_dashboard_links_to_project_settings(self):
        project = make_project(idea_json=json.dumps([idea_dict(1)]))
        html = _project_dashboard(project, derive_project_state(project, []))
        assert 'href="/projects/p1/settings"' in html
        assert ">Settings</a>" in html
        assert "New render" not in html

    async def test_project_with_ideas_shows_runs_section_and_hides_cta(self):
        project = make_project(idea_json=json.dumps([idea_dict(1), idea_dict(2)]))
        state = derive_project_state(project, [])
        html = _project_dashboard(project, state)
        assert "RUNS" in html
        assert "No runs yet" in html
        assert "Start Creating" not in html
        assert "2 ideas" in html

    async def test_stats_strip_shows_all_counts(self):
        project = make_project(idea_json=json.dumps([idea_dict(1, script=True)]))
        state = derive_project_state(project, [])
        html = _project_dashboard(project, state)
        for label in ("Ideas", "Scripts", "Videos", "Runs"):
            assert label in html

    async def test_active_run_enables_live_polling(self):
        project = make_project(idea_json=json.dumps([idea_dict(1, script=True)]))
        runs = [Run(id="r1", project_id="p1", status=RunStatus.RENDERING)]
        state = derive_project_state(project, runs)
        html = _project_dashboard(project, state)
        assert 'hx-trigger="every 20s"' in html
        assert "Render in progress" in html

    async def test_no_polling_without_active_run(self):
        project = make_project(idea_json=json.dumps([idea_dict(1, script=True)]))
        state = derive_project_state(project, [])
        assert 'hx-trigger="every 20s"' not in _project_dashboard(project, state)

    async def test_header_shows_format_and_caption_style_badges(self):
        project = Project(
            id="p1",
            topic="stoic",
            format="narrated",
            caption_style="plain",
            idea_json=json.dumps([idea_dict(1)]),
        )
        state = derive_project_state(project, [])
        html = _project_dashboard(project, state)
        assert "Narrated" in html
        assert "Plain" in html
        assert "Stoic" in html

    async def test_unknown_format_falls_back_to_raw_name(self):
        project = Project(
            id="p1",
            topic="stoic",
            format="weird",
            caption_style="highlight",
            idea_json=json.dumps([idea_dict(1)]),
        )
        state = derive_project_state(project, [])
        html = _project_dashboard(project, state)
        assert "weird" in html


class TestProjectCardStateChips:
    async def test_card_shows_state_chips(self):
        project = make_project(idea_json=json.dumps([idea_dict(1, script=True)]))
        state = derive_project_state(project, [])
        html = _ProjectCard(project, state)
        assert "1 idea" in html
        assert "1 script" in html

    async def test_card_without_state_has_no_chips(self):
        assert "ideas" not in _ProjectCard(make_project(), None)


def card_state_with_runs(runs):
    project = make_project(idea_json=json.dumps([idea_dict(1)]))
    return derive_project_state(project, runs)


class TestProjectCardRunStatus:
    async def test_card_shows_completed_pill(self):
        runs = [Run(id="r1", project_id="p1", status=RunStatus.COMPLETED)]
        assert "Completed" in _ProjectCard(make_project(), card_state_with_runs(runs))

    async def test_card_shows_failed_pill(self):
        runs = [Run(id="r1", project_id="p1", status=RunStatus.FAILED)]
        assert "Failed" in _ProjectCard(make_project(), card_state_with_runs(runs))

    async def test_card_prefers_active_run_over_history(self):
        runs = [
            Run(id="r1", project_id="p1", status=RunStatus.COMPLETED),
            Run(id="r2", project_id="p1", status=RunStatus.RENDERING),
        ]
        assert "Rendering" in _ProjectCard(make_project(), card_state_with_runs(runs))

    async def test_card_without_runs_has_no_status_pill(self):
        html = _ProjectCard(make_project(), card_state_with_runs([]))
        for label in ("Completed", "Failed", "Rendering", "Queued", "Draft"):
            assert label not in html


class FakeProjectService:
    def __init__(self, projects=None):
        self._projects = projects or []

    async def get(self, project_id):
        return next((p for p in self._projects if p.id == project_id), None)

    async def list_recent(self, limit=50):
        return self._projects[:limit]


class FakeRunService:
    async def list_recent(self, limit=50):
        return []

    async def list_by_project(self, project_id, limit=50):
        return []


class TestProjectsControllerState:
    async def test_list_projects_renders_with_runs_service(self):
        project = make_project(id="p1", idea_json=json.dumps([idea_dict(1)]))
        controller = ProjectsController(
            projects=FakeProjectService([project]), runs=FakeRunService()
        )
        html = str(await controller.list_projects(request=None))
        assert "p1" in html
        assert "Project Workspaces" in html

    async def test_list_header_uses_idea_and_video_copy(self):
        project = make_project(id="p1", idea_json=json.dumps([idea_dict(1)]))
        controller = ProjectsController(
            projects=FakeProjectService([project]), runs=FakeRunService()
        )
        html = str(await controller.list_projects(request=None))
        assert "ideas" in html
        assert "videos" in html


class TestDashboardContentSections:
    async def test_tab_bar_present_when_ideas_exist(self):
        project = make_project(idea_json=json.dumps([idea_dict(1)]))
        html = _project_dashboard(project, derive_project_state(project, []))
        assert 'href="/projects/p1"' in html
        assert ">Overview</a>" in html
        assert "Project Videos" in html
        assert 'href="/projects/p1/videos"' in html
        assert "Generate Ideas" in html
        assert 'href="/projects/p1/scripts"' in html
        assert "Settings" in html
        assert 'href="/projects/p1/settings"' in html
        assert "bg-primary text-primary-foreground border-primary" in html

    async def test_tab_bar_present_for_empty_project(self):
        project = make_project()
        html = _project_dashboard(project, derive_project_state(project, []))
        assert "Project Videos" in html
        assert "Generate Ideas" in html

    async def test_ideas_strip_shows_first_idea_with_script_link(self):
        project = make_project(idea_json=json.dumps([idea_dict(1), idea_dict(2)]))
        html = _project_dashboard(project, derive_project_state(project, []))
        assert "TOP IDEAS" in html
        assert "Idea 1" in html
        assert "Msg 1" in html
        assert "idea_index=0" in html
        assert "All 2 →" in html

    async def test_scripts_block_lists_script_meta(self):
        project = make_project(idea_json=json.dumps([idea_dict(1, script=True)]))
        html = _project_dashboard(project, derive_project_state(project, []))
        assert "SCRIPTS" in html
        assert "120 words" in html
        assert "30s" in html
        assert "idea_index=0" in html

    async def test_no_scripts_block_without_scripts(self):
        project = make_project(idea_json=json.dumps([idea_dict(1)]))
        html = _project_dashboard(project, derive_project_state(project, []))
        assert "SCRIPTS" not in html

    async def test_latest_render_card_shows_video_and_download(self, tmp_path):
        video = tmp_path / "v.mp4"
        video.write_bytes(b"v")
        project = make_project(idea_json=json.dumps([idea_dict(1)]))
        runs = [
            Run(
                id="rc",
                project_id="p1",
                status=RunStatus.COMPLETED,
                output_path=str(video),
                duration_s=44.0,
            )
        ]
        html = _project_dashboard(project, derive_project_state(project, runs))
        assert "LATEST RENDER" in html
        assert "/api/videos/download/rc" in html
        assert 'type="video/mp4"' in html
        assert 'id="latest-render"' in html

    async def test_latest_render_card_links_to_run_and_project(self):
        project = make_project(idea_json=json.dumps([idea_dict(1)]))
        runs = [
            Run(
                id="rc",
                project_id="p1",
                status=RunStatus.COMPLETED,
                output_path="/tmp/v.mp4",
                duration_s=44.0,
            )
        ]
        html = _project_dashboard(project, derive_project_state(project, runs))
        assert "/projects/p1/runs/rc" in html
        assert 'href="/projects/p1"' in html

    async def test_latest_render_card_shows_seo_panel_when_script_has_seo(self):
        seo = {
            "youtube_title": "T",
            "youtube_description": "D",
            "youtube_tags": "a,b",
            "facebook_caption": "F",
        }
        project = make_project(idea_json=json.dumps([idea_dict(1, script=True, seo=seo)]))
        runs = [
            Run(
                id="rc",
                project_id="p1",
                status=RunStatus.COMPLETED,
                output_path="/tmp/v.mp4",
                duration_s=44.0,
                selected_idea_id="idea1",
            )
        ]
        html = _project_dashboard(project, derive_project_state(project, runs))
        assert "SEO &amp; Social Distribution" in html or "SEO & Social Distribution" in html
        assert 'id="seo-youtube_title-idea1"' in html
        assert 'title="Save"' in html
        assert (
            'hx-post="/api/render/generate-seo?project_id=p1&amp;idea_id=idea1&amp;card=1"' in html
        )
        assert 'hx-target="#latest-render"' in html
        assert 'href="/projects/p1/scripts?idea_index=0"' in html

    async def test_latest_render_generate_seo_targets_latest_render(self):
        project = make_project(idea_json=json.dumps([idea_dict(1, script=True)]))
        runs = [
            Run(
                id="rc",
                project_id="p1",
                status=RunStatus.COMPLETED,
                output_path="/tmp/v.mp4",
                duration_s=44.0,
                selected_idea_id="idea1",
            )
        ]
        html = _project_dashboard(project, derive_project_state(project, runs))
        assert "Generate SEO" in html
        assert (
            'hx-post="/api/render/generate-seo?project_id=p1&amp;idea_id=idea1&amp;card=1"' in html
        )
        assert 'hx-target="#latest-render"' in html

    async def test_no_latest_render_card_without_completed_output(self):
        project = make_project(idea_json=json.dumps([idea_dict(1)]))
        runs = [Run(id="rf", project_id="p1", status=RunStatus.FAILED)]
        html = _project_dashboard(project, derive_project_state(project, runs))
        assert "LATEST RENDER" not in html

    async def test_profile_card_shows_resolved_values_and_settings_link(self):
        project = make_project(idea_json=json.dumps([idea_dict(1)]))
        html = _project_dashboard(
            project, derive_project_state(project, []), profile=make_profile()
        )
        assert "EFFECTIVE PROFILE" in html
        assert "30s" in html
        assert "1080×1920" in html
        assert 'href="/projects/p1/settings"' in html
        assert "Edit Settings →" in html

    async def test_profile_card_skipped_without_profile(self):
        project = make_project(idea_json=json.dumps([idea_dict(1)]))
        html = _project_dashboard(project, derive_project_state(project, []), profile=None)
        assert "EFFECTIVE PROFILE" not in html

    async def test_failed_run_shows_error_and_idea_title(self):
        project = make_project(idea_json=json.dumps([idea_dict(1, title="Scroll Story")]))
        runs = [
            Run(
                id="rf",
                project_id="p1",
                status=RunStatus.FAILED,
                selected_idea_id="idea1",
                error="ffmpeg exited with code 1",
            )
        ]
        html = _project_dashboard(project, derive_project_state(project, runs))
        assert "Error encountered: " in html
        assert "ffmpeg exited with code 1" in html
        assert "Scroll Story" in html
        assert "</a><p" in html

    async def test_completed_run_uses_idea_title(self):
        project = make_project(idea_json=json.dumps([idea_dict(1, title="Scroll Story")]))
        runs = [
            Run(
                id="rc",
                project_id="p1",
                status=RunStatus.COMPLETED,
                selected_idea_id="idea1",
                output_path="/tmp/v.mp4",
            )
        ]
        html = _project_dashboard(project, derive_project_state(project, runs))
        assert "Scroll Story" in html
        assert "Render Run" not in html

    async def test_contract_banner_renders_remap_form_without_escaped_markup(self):
        issues = [ContractIssue(Severity.ERROR, "FORMAT_NOT_LOADED", "format not loaded")]
        html = _project_dashboard(
            make_project(), derive_project_state(make_project(), []), issues=issues
        )
        assert "Topic/format contract" in html
        assert "FORMAT_NOT_LOADED" in html
        assert "format not loaded" in html
        assert '<select name="format_name"' in html
        assert 'hx-post="/api/projects/p1/format/remap"' in html
        assert "Re-map →" in html
        assert "&lt;li" not in html
        assert "<li>" in html


class FakeFormRequest:
    def __init__(self, form_data):
        self._form_data = form_data

    async def form(self):
        return self._form_data


class RemapProjectService(FakeProjectService):
    def __init__(self, projects=None):
        super().__init__(projects)
        self.saved_updates = None

    async def save_profile_overrides(self, project_id, updates):
        self.saved_updates = (project_id, updates)


class TestFormatRemap:
    async def test_remap_saves_valid_format(self):
        project = make_project(id="p1", idea_json=json.dumps([idea_dict(1)]))
        service = RemapProjectService([project])
        controller = ProjectsController(projects=service)
        html = str(
            await controller.remap_project_format(FakeFormRequest({"format_name": "topn"}), id="p1")
        )
        assert service.saved_updates == (
            "p1",
            __import__(
                "shorts_creator.models.project_profile", fromlist=["ProjectProfileOverrides"]
            ).ProjectProfileOverrides(format_name="topn"),
        )
        assert "window.location.reload" in html

    async def test_remap_rejects_unknown_format(self):
        project = make_project(id="p1", idea_json=json.dumps([idea_dict(1)]))
        service = RemapProjectService([project])
        controller = ProjectsController(projects=service)
        html = str(
            await controller.remap_project_format(
                FakeFormRequest({"format_name": "bogus"}), id="p1"
            )
        )
        assert service.saved_updates is None
        assert "Could not re-map format" in html

    async def test_remap_requires_existing_project(self):
        controller = ProjectsController(projects=RemapProjectService([]))
        response = await controller.remap_project_format(
            FakeFormRequest({"format_name": "topn"}), id="nope"
        )
        assert response.status_code == 404
