from typing import get_args, get_type_hints

from shorts_creator.controllers.api.settings_api import SettingsApiController
from shorts_creator.controllers.project_settings import ProjectSettingsController
from shorts_creator.controllers.render import RenderController
from shorts_creator.models.project_profile import EffectiveProjectProfile
from shorts_creator.services.project_profile_service import ProjectProfileService


def test_framework_compose_importable():
    from lexigram.multimedia.video.config import VideoProcessingConfig
    from lexigram.multimedia.video.processing.ffmpeg import FFmpegVideoProcessor

    processor = FFmpegVideoProcessor(config=VideoProcessingConfig())
    assert processor is not None


def _profile_service_annotation(cls) -> type:
    hints = get_type_hints(cls.__init__)
    profile_service = hints.get("profile_service")
    assert profile_service is not None, f"{cls.__name__} lost its profile_service param"
    return profile_service


def test_render_and_project_settings_annotate_shared_profile_service():
    assert ProjectProfileService in get_args(_profile_service_annotation(RenderController))
    assert ProjectProfileService in get_args(_profile_service_annotation(ProjectSettingsController))
    assert ProjectProfileService in get_args(_profile_service_annotation(SettingsApiController))


def test_profile_service_params_default_to_none():
    import inspect

    for cls in (RenderController, ProjectSettingsController, SettingsApiController):
        param = inspect.signature(cls.__init__).parameters["profile_service"]
        assert param.default is None, f"{cls.__name__} lost the optional profile_service default"


class FakeProfileService:
    """Records resolve() calls and returns a minimal effective profile."""

    def __init__(self):
        self.resolve_calls = []

    async def resolve(self, project):
        self.resolve_calls.append(project)
        return EffectiveProjectProfile(
            duration_seconds=30.0,
            cta_enabled=False,
            cta_lead_in_seconds=0.0,
            cta_display_seconds=0.0,
            caption_style="highlight",
            format_name="narrated",
            topic="self_improvement",
            reel_width=1080,
            reel_height=1920,
        )

    async def validate_pair_for_project(self, project):
        return []


class _FakeProject:
    id = "p1"
    title = "Fake Project"
    topic = "self_improvement"
    profile_overrides_json = "{}"
    idea_json = None

    def model_copy(self, *, update=None):
        dup = _FakeProject.__new__(_FakeProject)
        dup.__dict__.update(self.__dict__)
        if update:
            dup.__dict__.update(update)
        return dup


class _FakeProjectService:
    async def get(self, project_id):
        return _FakeProject()


class _FakeRunService:
    async def get(self, run_id):
        return None

    async def list_by_project(self, project_id, limit=50):
        return []


class _FakeIdeaService:
    pass


class _FakeScriptService:
    _last_script = None

    @property
    def last_script(self):
        return self._last_script


class _FakeConfig:
    default_duration = 30
    reel_width = 1080
    reel_height = 1920


class _FakeSettingsStore:
    async def get_overrides(self):
        return {}


async def test_render_page_resolves_profile_exactly_once():
    fake = FakeProfileService()
    controller = RenderController(
        ideas=_FakeIdeaService(),
        scripts=_FakeScriptService(),
        config=_FakeConfig(),
        runs=_FakeRunService(),
        project_service=_FakeProjectService(),
        store=_FakeSettingsStore(),
        profile_service=fake,
    )
    request = type("Request", (), {"query_params": {}, "headers": {}})()
    await controller.render_page(request=request, id="p1")
    assert len(fake.resolve_calls) == 1


async def test_project_settings_page_resolves_profile_twice():
    """The settings page resolves the effective profile and a second pass
    with the project's overrides suppressed (the knobs' builtin reset
    targets), Task 4/E1."""
    fake = FakeProfileService()
    controller = ProjectSettingsController(
        config=_FakeConfig(),
        projects=_FakeProjectService(),
        store=_FakeSettingsStore(),
        profile_service=fake,
    )
    await controller.project_settings(request=None, id="p1")
    assert len(fake.resolve_calls) == 2
    assert fake.resolve_calls[0] is not fake.resolve_calls[1]
    for project in fake.resolve_calls:
        assert project.profile_overrides_json == "{}"


async def test_settings_api_get_settings_resolves_profile_exactly_once():
    fake = FakeProfileService()
    controller = SettingsApiController(
        config=_FakeConfig(),
        store=_FakeSettingsStore(),
        profile_service=fake,
    )
    await controller.get_settings()
    assert len(fake.resolve_calls) == 1
    assert fake.resolve_calls[0].topic == ""
