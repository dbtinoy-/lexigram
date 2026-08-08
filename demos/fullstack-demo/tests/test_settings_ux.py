import json
from datetime import UTC, datetime
from pathlib import Path

from shorts_creator.controllers.project_runs import _run_dashboard, _run_panel
from shorts_creator.controllers.projects import _project_dashboard
from shorts_creator.models.project import Project
from shorts_creator.models.run import Run, RunStatus
from shorts_creator.services.project_state import derive_project_state
from shorts_creator.ui.components.pipeline_tracker import PipelineTracker
from shorts_creator.ui.shell import AppLayout

STATIC_JS = Path(__file__).resolve().parents[1] / "src/shorts_creator/ui/static/js"

# ──────────────────────────────────────────────
# Shell navigation (Task 8 Step 1/3)
# ──────────────────────────────────────────────


class TestSidebarNavigation:
    def test_sidebar_has_configure_order_and_canonical_topics(self):
        html = AppLayout()._sidebar()
        assert html.index("Assets") < html.index("Topics") < html.index("Settings")
        assert "/topics" in html
        assert "/video-types" not in html

    def test_sidebar_keeps_active_context_groups(self):
        html = AppLayout()._sidebar()
        assert 'id="sidebar-recent-projects"' in html
        assert "/api/sidebar/recent-projects" in html

    def test_shell_script_guards_unsaved_profile_changes(self):
        html = AppLayout().render_body_end()
        assert 'src="/static/js/htmx-shell.js"' in html
        js = (STATIC_JS / "htmx-shell.js").read_text()
        assert "project-profile-form" in js
        assert "data-dirty" in js


# ──────────────────────────────────────────────
# Pipeline tracker (Task 8 step 4)
# ──────────────────────────────────────────────


class TestPipelineTrackerCanonical:
    def test_pipeline_tracker_uses_only_ideas_script_render(self):
        html = str(PipelineTracker(current="ideas", project_id="project-1", density="compact"))
        assert all(label in html for label in ("Ideas", "Script", "Render"))
        assert "Videos" not in html

    def test_full_density_shows_previews_without_videos(self):
        html = str(
            PipelineTracker(
                current="render",
                project_id="p1",
                density="full",
                stage_state=[
                    {"done": True, "active": False, "preview": "3 ideas"},
                    {"done": True, "active": False, "preview": "30s · 120 words"},
                    {"done": False, "active": True, "preview": ""},
                ],
            )
        )
        assert "3 ideas" in html
        assert "30s · 120 words" in html
        assert "Videos" not in html


# ──────────────────────────────────────────────
# Project dashboard — always a runs list (Task 8 step 5)
# ──────────────────────────────────────────────


def make_project(id="p1", idea_json=None):
    return Project(id=id, topic="self_improvement", idea_json=idea_json)


def make_run(id="r1", status=RunStatus.DRAFT, idea_json=None):
    created = datetime(2026, 7, 24, 9, 11, tzinfo=UTC)
    project = make_project(idea_json=idea_json)
    runs = [Run(id=id, project_id="p1", title=f"Run {id}", status=status, created_at=created)]
    return project, derive_project_state(project, runs)


class TestProjectDashboardRunsList:
    async def test_dashboard_always_uses_runs_list_for_single_run(self):
        project, state = make_run(
            "r1",
            RunStatus.COMPLETED,
            json.dumps([{"id": "i1", "title": "Idea 1", "core_message": "M"}]),
        )
        html = _project_dashboard(project, state)
        assert "RUNS" in html
        assert "Open →" in html

    async def test_dashboard_run_rows_link_to_run_dashboard(self):
        project, state = make_run(
            "r1",
            RunStatus.COMPLETED,
            json.dumps([{"id": "i1", "title": "Idea 1", "core_message": "M"}]),
        )
        html = _project_dashboard(project, state)
        assert "/projects/p1/runs/r1" in html
        assert "completed" in html

    async def test_dashboard_without_runs_offers_new_run_link(self):
        project = make_project(
            idea_json=json.dumps([{"id": "i1", "title": "Idea 1", "core_message": "M"}])
        )
        state = derive_project_state(project, [])
        html = _project_dashboard(project, state)
        assert "RUNS" in html
        assert "No runs yet" in html
        assert "/projects/p1/scripts" in html


# ──────────────────────────────────────────────
# Run dashboard reuses the shared tracker (Task 8 step 4)
# ──────────────────────────────────────────────


class TestRunDashboardSharedTracker:
    def test_run_panel_uses_shared_pipeline_tracker(self):
        project = make_project(
            idea_json=json.dumps([{"id": "i1", "title": "I1", "core_message": "M"}])
        )
        run = Run(id="r1", project_id="p1", title="Run r1", status=RunStatus.SCRIPT_READY)
        html = _run_panel(project, run)
        assert "text-[11px] font-bold font-mono tracking-wider uppercase" in html
        for label in ("Ideas", "Script", "Render"):
            assert label in html
        assert "Videos" not in html

    def test_run_dashboard_full_page_renders_shell(self):
        project = make_project()
        run = Run(id="r1", project_id="p1", title="Run r1", status=RunStatus.SCRIPT_READY)
        html = _run_dashboard(project, run)
        assert "← Project" in html
        assert "Ideas" in html and "Script" in html and "Render" in html
        assert "Run r1" in html
