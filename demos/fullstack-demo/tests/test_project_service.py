import json
import uuid

import pytest

from shorts_creator.models.project import Project
from shorts_creator.models.run import Run, RunStatus
from shorts_creator.services.project_service import ProjectService
from shorts_creator.services.run_service import RunService


class _FakeProjectRepo:
    def __init__(self):
        self.store: dict[str, Project] = {}

    async def create(self, project):
        self.store[project.id] = project
        return project

    async def update(self, project):
        self.store[project.id] = project
        return project

    async def get(self, project_id):
        return self.store.get(project_id)

    async def list_recent(self, limit=50):
        return list(self.store.values())[:limit]


class _FakeRunRepo:
    def __init__(self):
        self.store: dict[str, Run] = {}

    async def create(self, run):
        self.store[run.id] = run
        return run

    async def update(self, run):
        self.store[run.id] = run
        return run

    async def get(self, run_id):
        return self.store.get(run_id)

    async def list_by_project(self, project_id, limit=50):
        return [r for r in self.store.values() if r.project_id == project_id][:limit]

    async def list_recent(self, limit=50):
        return list(self.store.values())[:limit]


@pytest.fixture
def project_service():
    return ProjectService(_FakeProjectRepo())


@pytest.fixture
def run_service():
    return RunService(_FakeRunRepo())


class TestProjectService:
    async def test_get_project(self, project_service):
        p = Project(id="p1", topic="self_improvement", focus="habits", title="Test Project")
        await project_service.repo.create(p)
        found = await project_service.get(p.id)
        assert found is not None
        assert found.id == p.id


class TestProjectServiceIdeaCrud:
    async def test_save_ideas_roundtrip(self, project_service):
        await project_service.repo.create(Project(id="p1", topic="self_improvement"))
        ideas = [{"id": str(uuid.uuid4()), "title": "Idea 1", "core_message": "Msg 1"}]
        updated = await project_service.save_ideas("p1", ideas)
        assert updated.idea_json is not None
        parsed = json.loads(updated.idea_json)
        assert len(parsed) == 1
        assert parsed[0]["title"] == "Idea 1"

    async def test_delete_idea_by_id(self, project_service):
        idea_id = str(uuid.uuid4())
        await project_service.repo.create(Project(id="p2", topic="self_improvement"))
        ideas = [
            {"id": idea_id, "title": "Idea 1", "core_message": "Msg 1"},
            {"id": str(uuid.uuid4()), "title": "Idea 2", "core_message": "Msg 2"},
        ]
        await project_service.save_ideas("p2", ideas)
        updated = await project_service.delete_idea("p2", idea_id)
        parsed = json.loads(updated.idea_json)
        assert len(parsed) == 1
        assert parsed[0]["title"] == "Idea 2"

    async def test_delete_idea_not_found_raises(self, project_service):
        await project_service.repo.create(Project(id="p3", topic="self_improvement"))
        await project_service.save_ideas("p3", [{"id": "abc", "title": "X", "core_message": "M"}])
        with pytest.raises(ValueError, match="Idea not found"):
            await project_service.delete_idea("p3", "nonexistent")

    async def test_update_idea_by_id(self, project_service):
        idea_id = str(uuid.uuid4())
        await project_service.repo.create(Project(id="p4", topic="self_improvement"))
        await project_service.save_ideas(
            "p4", [{"id": idea_id, "title": "Old", "core_message": "M"}]
        )
        await project_service.update_idea("p4", idea_id, {"title": "New"})
        updated = await project_service.get("p4")
        parsed = json.loads(updated.idea_json)
        assert parsed[0]["title"] == "New"

    async def test_prepend_ideas(self, project_service):
        await project_service.repo.create(Project(id="p5", topic="self_improvement"))
        await project_service.save_ideas("p5", [{"id": "a", "title": "A", "core_message": "M"}])
        new = [{"id": "b", "title": "B", "core_message": "M"}]
        updated = await project_service.prepend_ideas("p5", new)
        parsed = json.loads(updated.idea_json)
        assert [i["title"] for i in parsed] == ["B", "A"]

    async def test_get_idea_by_id(self, project_service):
        idea_id = str(uuid.uuid4())
        await project_service.repo.create(Project(id="p6", topic="self_improvement"))
        await project_service.save_ideas("p6", [{"id": idea_id, "title": "T", "core_message": "M"}])
        idea = await project_service.get_idea_by_id("p6", idea_id)
        assert idea is not None
        assert idea["title"] == "T"

    async def test_get_idea_by_id_not_found(self, project_service):
        await project_service.repo.create(Project(id="p7", topic="self_improvement"))
        idea = await project_service.get_idea_by_id("p7", "nonexistent")
        assert idea is None

    async def test_save_and_get_script(self, project_service):
        idea_id = str(uuid.uuid4())
        await project_service.repo.create(Project(id="p8", topic="self_improvement"))
        await project_service.save_ideas("p8", [{"id": idea_id, "title": "T", "core_message": "M"}])
        script = {"title": "Script 1", "sections": []}
        await project_service.save_script("p8", idea_id, script)
        fetched = await project_service.get_script("p8", idea_id)
        assert fetched is not None
        assert fetched["title"] == "Script 1"

    async def test_get_script_no_idea_returns_none(self, project_service):
        await project_service.repo.create(Project(id="p9", topic="self_improvement"))
        fetched = await project_service.get_script("p9", "nonexistent")
        assert fetched is None

    async def test_get_script_none_when_no_script(self, project_service):
        idea_id = str(uuid.uuid4())
        await project_service.repo.create(Project(id="p10", topic="self_improvement"))
        await project_service.save_ideas(
            "p10", [{"id": idea_id, "title": "T", "core_message": "M"}]
        )
        fetched = await project_service.get_script("p10", idea_id)
        assert fetched is None


class TestRunService:
    async def test_create_run(self, run_service):
        r = await run_service.create(project_id="p1", title="Run #1")
        assert r.project_id == "p1"
        assert r.status == RunStatus.DRAFT

    async def test_status_transitions(self, run_service):
        r = await run_service.create(project_id="p1", title="Run #1")
        await run_service.mark_rendering(r.id)
        await run_service.mark_completed(r.id, output_path="/out.mp4", duration_s=32.0)
        updated = await run_service.get(r.id)
        assert updated.status == RunStatus.COMPLETED
        assert updated.output_path == "/out.mp4"
        assert updated.duration_s == 32.0

    async def test_mark_failed_records_error(self, run_service):
        r = await run_service.create(project_id="p1", title="Run #1")
        await run_service.mark_rendering(r.id)
        await run_service.mark_failed(r.id, error="TTS timeout")
        updated = await run_service.get(r.id)
        assert updated.status == RunStatus.FAILED
        assert updated.error == "TTS timeout"
