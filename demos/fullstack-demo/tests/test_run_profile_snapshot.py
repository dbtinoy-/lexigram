import json

import pytest

from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProfileSource,
    ResolvedSetting,
)
from shorts_creator.models.run import Run, RunStatus
from shorts_creator.services.run_service import RunService


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


@pytest.fixture
def run_service() -> RunService:
    return RunService(repo=_FakeRunRepo())


class TestCreateWithProfile:
    async def test_create_run_persists_profile_snapshot(self, run_service):
        profile = EffectiveProjectProfile(
            duration_seconds=ResolvedSetting(45, ProfileSource.PROJECT, True),
            caption_style=ResolvedSetting("highlight", ProfileSource.FORMAT, False),
        )
        run = await run_service.create_with_profile("project-1", "Idea", profile)
        assert json.loads(run.settings_snapshot_json)["duration_seconds"] == 45

    async def test_get_snapshot_returns_decoded_values(self, run_service):
        run = await run_service.repo.create(
            Run(project_id="project-1", settings_snapshot_json='{"duration_seconds": 30}')
        )
        snapshot = await run_service.get_snapshot(run.id)
        assert snapshot == {"duration_seconds": 30}

    async def test_get_snapshot_returns_none_without_snapshot(self, run_service):
        run = await run_service.repo.create(Run(project_id="project-1"))
        assert await run_service.get_snapshot(run.id) is None


class TestSnapshotMutationGuard:
    async def test_completed_run_snapshot_is_not_rewritten(self, run_service):
        run = Run(
            project_id="project-1",
            settings_snapshot_json='{"duration_seconds": 45}',
            status=RunStatus.COMPLETED,
        )
        await run_service.repo.create(run)
        with pytest.raises(ValueError, match="immutable"):
            await run_service.update_profile_snapshot(run.id, {"duration_seconds": 60})

    async def test_rendering_run_snapshot_is_not_rewritten(self, run_service):
        run = Run(
            project_id="project-1",
            settings_snapshot_json='{"duration_seconds": 45}',
            status=RunStatus.RENDERING,
        )
        await run_service.repo.create(run)
        with pytest.raises(ValueError, match="immutable"):
            await run_service.update_profile_snapshot(run.id, {"caption_style": "plain"})

    async def test_draft_run_snapshot_can_be_updated(self, run_service):
        run = Run(
            project_id="project-1",
            settings_snapshot_json='{"duration_seconds": 45}',
            status=RunStatus.DRAFT,
        )
        await run_service.repo.create(run)
        updated = await run_service.update_profile_snapshot(run.id, {"duration_seconds": 60})
        snapshot = await run_service.get_snapshot(run.id)
        assert snapshot["duration_seconds"] == 60
        assert updated.id == run.id
