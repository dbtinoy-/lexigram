from shorts_creator.models.project_profile import ProjectProfileOverrides
from shorts_creator.services.project_service import (
    ProfileValidationError,
    ProjectService,
)


class _FakeRepo:
    def __init__(self):
        self.rows = {}

    async def get(self, project_id):
        return self.rows.get(project_id)

    async def update(self, project):
        self.rows[project.id] = project
        return project


def _project(overrides=None):
    from shorts_creator.models.project import Project

    project = Project(topic="self_improvement")
    if overrides:
        import json

        project.profile_overrides_json = json.dumps(overrides, separators=(",", ":"))
    return project


class TestSaveProfileOverrides:
    async def test_merges_only_submitted_keys(self):
        project = _project({"duration_seconds": 30, "caption_style": "plain"})
        service = ProjectService(_FakeRepo())
        service.repo.rows[project.id] = project

        saved = await service.save_profile_overrides(
            project.id,
            ProjectProfileOverrides(duration_seconds=45),
        )

        assert saved.id == project.id
        assert _overrides(saved) == {"duration_seconds": 45, "caption_style": "plain"}

    async def test_invalid_duration_raises_profile_validation_error(self):
        project = _project({})
        service = ProjectService(_FakeRepo())
        service.repo.rows[project.id] = project

        try:
            await service.save_profile_overrides(
                project.id,
                ProjectProfileOverrides(duration_seconds=-5),
            )
        except ProfileValidationError as exc:
            assert exc.errors == {"duration_seconds": "must be greater than zero"}
            assert _overrides(project) == {}
        else:
            raise AssertionError("expected ProfileValidationError")

    async def test_invalid_caption_style_reported_per_field(self):
        project = _project({})
        service = ProjectService(_FakeRepo())
        service.repo.rows[project.id] = project

        try:
            await service.save_profile_overrides(
                project.id,
                ProjectProfileOverrides(caption_style="fancy"),
            )
        except ProfileValidationError as exc:
            assert "caption_style" in exc.errors
        else:
            raise AssertionError("expected ProfileValidationError")

    async def test_missing_project_raises_value_error(self):
        service = ProjectService(_FakeRepo())
        try:
            await service.save_profile_overrides("nope", ProjectProfileOverrides())
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")


class TestResetProfileOverride:
    async def test_reset_removes_single_key(self):
        project = _project({"duration_seconds": 45, "caption_style": "plain"})
        service = ProjectService(_FakeRepo())
        service.repo.rows[project.id] = project

        saved = await service.reset_profile_override(project.id, "duration_seconds")

        assert _overrides(saved) == {"caption_style": "plain"}

    async def test_reset_missing_key_is_noop(self):
        project = _project({"duration_seconds": 30})
        service = ProjectService(_FakeRepo())
        service.repo.rows[project.id] = project

        saved = await service.reset_profile_override(project.id, "asset_music_id")

        assert _overrides(saved) == {"duration_seconds": 30}

    async def test_reset_all_clears_overrides(self):
        project = _project({"duration_seconds": 30, "caption_style": "plain"})
        service = ProjectService(_FakeRepo())
        service.repo.rows[project.id] = project

        saved = await service.reset_all_profile_overrides(project.id)

        assert _overrides(saved) == {}


def _overrides(project) -> dict:
    import json

    try:
        return json.loads(project.profile_overrides_json or "{}")
    except (TypeError, ValueError):
        return {}
