from shorts_creator.controllers.project_runs import _run_panel
from shorts_creator.models.project import Project
from shorts_creator.models.run import Run, RunStatus


class TestRunPanelEmptyProject:
    async def test_no_ideas_stage_is_active(self):
        project = Project(id="p1", topic="self_improvement")
        run = Run(id="r1", project_id="p1", status=RunStatus.DRAFT)
        html = _run_panel(project, run)
        assert "Ideas Generated" not in html
        assert "Generate Ideas" in html
