import pytest

from shorts_creator.models.run import Run, RunStatus
from shorts_creator.services.run_service import InvalidTransitionError, RunService


class TestDeadTransitionCodeRemoved:
    @pytest.mark.asyncio
    async def test_mark_queued_no_longer_exists(self):
        assert not hasattr(RunService, "mark_queued")

    def test_queued_status_enum_kept_for_ui(self):
        assert RunStatus.QUEUED.value == "queued"

    @pytest.mark.asyncio
    async def test_draft_to_rendering_direct_still_works(self):
        repo = _FakeRunRepo()
        svc = RunService(repo)
        run = await repo.create(Run(project_id="p1"))
        await svc.mark_rendering(run.id)
        assert repo.store[run.id].status is RunStatus.RENDERING


class TestStaleDraftSweep:
    @pytest.mark.asyncio
    async def test_aged_draft_failed_at_sweep(self):
        from datetime import UTC, datetime, timedelta

        from shorts_creator.models.run import Run, RunStatus
        from shorts_creator.services.module import _fail_stale_draft_runs

        repo = _FakeRunRepo()
        svc = RunService(repo)
        aged = await repo.create(Run(project_id="p1"))
        aged.created_at = datetime.now(UTC) - timedelta(minutes=5)

        await _fail_stale_draft_runs(svc)

        assert repo.store[aged.id].status is RunStatus.FAILED
        assert "Interrupted before rendering" in repo.store[aged.id].error

    @pytest.mark.asyncio
    async def test_fresh_draft_failed_at_sweep(self):
        from shorts_creator.models.run import Run, RunStatus
        from shorts_creator.services.module import _fail_stale_draft_runs

        repo = _FakeRunRepo()
        svc = RunService(repo)
        fresh = await repo.create(Run(project_id="p1"))

        await _fail_stale_draft_runs(svc)

        assert repo.store[fresh.id].status is RunStatus.FAILED
        assert "Interrupted before rendering" in repo.store[fresh.id].error

    @pytest.mark.asyncio
    async def test_sweep_leaves_other_statuses_alone(self):
        from datetime import UTC, datetime, timedelta

        from shorts_creator.models.run import Run, RunStatus
        from shorts_creator.services.module import _fail_stale_draft_runs

        repo = _FakeRunRepo()
        svc = RunService(repo)
        done = await repo.create(Run(project_id="p1"))
        done.status = RunStatus.COMPLETED
        done.created_at = datetime.now(UTC) - timedelta(hours=2)
        await repo.update(done)
        fresh = await repo.create(Run(project_id="p1"))

        await _fail_stale_draft_runs(svc)

        assert repo.store[done.id].status is RunStatus.COMPLETED
        assert repo.store[fresh.id].status is RunStatus.FAILED


class TestInvalidTransitionError:
    def test_message_and_attrs(self):
        err = InvalidTransitionError(RunStatus.DRAFT, RunStatus.RENDERING)
        assert "DRAFT" in str(err)
        assert "RENDERING" in str(err)
        assert err.current == RunStatus.DRAFT
        assert err.target == RunStatus.RENDERING


class TestInvalidTransitionRaised:
    @pytest.mark.asyncio
    async def test_invalid_transition_raises(self):
        repo = _FakeRunRepo()
        svc = RunService(repo)
        run = await repo.create(Run(project_id="p1"))
        with pytest.raises(InvalidTransitionError, match="DRAFT.*COMPLETED"):
            await svc.mark_completed(run.id, "/out.mp4", 10.0)

    @pytest.mark.asyncio
    async def test_completed_to_rendering_rejected(self):
        repo = _FakeRunRepo()
        svc = RunService(repo)
        run = await repo.create(Run(project_id="p1"))
        await svc.mark_rendering(run.id)
        await svc.mark_completed(run.id, "/out.mp4", 10.0)
        with pytest.raises(InvalidTransitionError, match="COMPLETED.*RENDERING"):
            await svc.mark_rendering(run.id)

    @pytest.mark.asyncio
    async def test_failed_to_rendering_still_allowed(self):
        repo = _FakeRunRepo()
        svc = RunService(repo)
        run = await repo.create(Run(project_id="p1"))
        await svc.mark_rendering(run.id)
        await svc.mark_failed(run.id, "TTS timeout")
        await svc.mark_rendering(run.id)
        assert repo.store[run.id].status is RunStatus.RENDERING


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

    async def list_status(self, status, limit=10_000):
        return [r for r in self.store.values() if r.status == status][:limit]
