import json

from shorts_creator.models.project import Project
from shorts_creator.models.run import Run, RunStatus
from shorts_creator.services.project_state import derive_project_state, parse_idea_json

SCRIPT = {"title": "S", "sections": [], "total_duration": 30, "word_count": 120, "pacing_wps": 4.0}


def make_project(id="p1", idea_json=None):
    return Project(id=id, topic="self_improvement", idea_json=idea_json)


def make_run(status=RunStatus.DRAFT, idea_id=None, output=None, duration=None, pid="p1", rid="r1"):
    return Run(
        id=rid,
        project_id=pid,
        status=status,
        selected_idea_id=idea_id,
        output_path=output,
        duration_s=duration,
    )


def idea_dict(i, script=False):
    d = {
        "id": f"idea{i}",
        "title": f"Idea {i}",
        "core_message": f"Msg {i}",
        "quotability_score": 7.0,
    }
    if script:
        d["script_json"] = json.dumps(SCRIPT)
    return d


class TestParseIdeaJson:
    async def test_none_and_invalid_return_empty(self):
        assert parse_idea_json(None) == []
        assert parse_idea_json("not json") == []

    async def test_single_dict_wrapped_in_list(self):
        assert parse_idea_json(json.dumps({"id": "a"})) == [{"id": "a"}]

    async def test_list_passthrough(self):
        assert parse_idea_json(json.dumps([{"id": "a"}, {"id": "b"}])) == [{"id": "a"}, {"id": "b"}]


class TestDeriveEmptyProject:
    async def test_empty_project(self):
        state = derive_project_state(make_project(), [])
        assert state.ideas == []
        assert state.stage == "ideas"
        assert state.script_indices == set()
        assert state.rendered_indices == set()
        assert state.active_run is None
        assert state.latest_run is None
        assert state.stats == {"ideas": 0, "scripts": 0, "videos": 0, "runs": 0}
        assert [s["done"] for s in state.stage_state] == [False, False, False]
        assert [s["key"] for s in state.stage_state] == ["ideas", "script", "render"]


class TestDeriveStages:
    async def test_ideas_without_script_is_script_stage(self):
        project = make_project(idea_json=json.dumps([idea_dict(1), idea_dict(2)]))
        state = derive_project_state(project, [])
        assert state.stage == "script"
        assert state.script_indices == set()
        assert state.stats["ideas"] == 2
        assert state.stage_state[0]["done"] is True
        assert state.stage_state[0]["preview"] == "2 ideas"
        assert state.stage_state[1]["active"] is True

    async def test_script_ready_is_render_stage(self):
        project = make_project(idea_json=json.dumps([idea_dict(1, script=True)]))
        state = derive_project_state(project, [])
        assert state.script_indices == {0}
        assert state.stage == "render"
        assert state.stage_state[1]["done"] is True
        assert state.stage_state[1]["preview"] == "30s · 120 words"
        assert state.stage_state[2]["active"] is True

    async def test_completed_render_with_existing_file_is_done(self, tmp_path):
        out = tmp_path / "video.mp4"
        out.write_bytes(b"x")
        project = make_project(idea_json=json.dumps([idea_dict(1, script=True)]))
        runs = [
            make_run(status=RunStatus.COMPLETED, idea_id="idea1", output=str(out), duration=29.5)
        ]
        state = derive_project_state(project, runs)
        assert state.rendered_indices == {0}
        assert state.stage == "done"
        assert state.stats["videos"] == 1
        assert state.stage_state[2]["done"] is True
        assert state.stage_state[2]["preview"] == "29.5s video"

    async def test_missing_output_file_is_not_rendered(self):
        project = make_project(idea_json=json.dumps([idea_dict(1, script=True)]))
        runs = [make_run(status=RunStatus.COMPLETED, idea_id="idea1", output="/does/not/exist.mp4")]
        state = derive_project_state(project, runs)
        assert state.rendered_indices == set()
        assert state.stage == "render"


class TestDeriveRuns:
    async def test_active_run_detected(self):
        runs = [
            make_run(status=RunStatus.RENDERING, rid="live"),
            make_run(status=RunStatus.COMPLETED, rid="old", idea_id="idea1"),
        ]
        state = derive_project_state(make_project(), runs)
        assert state.active_run is not None
        assert state.active_run.id == "live"
        assert state.latest_run.id == "live"

    async def test_active_run_found_outside_latest(self):
        runs = [
            make_run(status=RunStatus.DRAFT, rid="newest"),
            make_run(status=RunStatus.RENDERING, rid="live"),
        ]
        state = derive_project_state(make_project(), runs)
        assert state.active_run is not None
        assert state.active_run.id == "live"
        assert state.latest_run.id == "newest"

    async def test_queued_counts_as_active(self):
        runs = [make_run(status=RunStatus.QUEUED, rid="q1")]
        state = derive_project_state(make_project(), runs)
        assert state.active_run is not None
        assert state.active_run.id == "q1"

    async def test_failed_run_does_not_render(self):
        project = make_project(idea_json=json.dumps([idea_dict(1, script=True)]))
        runs = [make_run(status=RunStatus.FAILED, idea_id="idea1")]
        state = derive_project_state(project, runs)
        assert state.rendered_indices == set()
        assert state.stage == "render"
