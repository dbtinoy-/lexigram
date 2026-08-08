from shorts_creator.models.project import Project
from shorts_creator.models.run import Run, RunStatus


class TestProjectModel:
    def test_project_defaults(self):
        p = Project(id="p1", topic="self_improvement", focus="habits")
        assert p.id == "p1"
        assert p.topic == "self_improvement"
        assert p.focus == "habits"


class TestRunModel:
    def test_run_defaults(self):
        r = Run(id="r1", project_id="p1", title="Test Run")
        assert r.status == RunStatus.DRAFT
        assert r.selected_idea_id is None
        assert r.stage_progress == {}
        assert r.duration_s is None
        assert r.error is None

    def test_status_is_str_enum(self):
        assert RunStatus.RENDERING == "rendering"
        assert RunStatus.RENDERING.value == "rendering"
