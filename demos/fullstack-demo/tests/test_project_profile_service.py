import json

import pytest

from shorts_creator.formats import registry as format_registry
from shorts_creator.models.project import Project
from shorts_creator.models.project_profile import ProfileSource
from shorts_creator.services.core import AppConfig
from shorts_creator.services.project_profile_service import ProjectProfileService

CONFIG = AppConfig.from_dict(
    {
        "reel_width": 1080,
        "reel_height": 1920,
        "default_duration": 30.0,
    }
)

_BUILTIN_MIDPOINT = (
    format_registry.get("narrated").duration_range[0]
    + format_registry.get("narrated").duration_range[1]
) // 2


@pytest.fixture
def profile_service():
    return ProjectProfileService(
        config=CONFIG,
    )


class TestProjectProfilePrecedence:
    async def test_project_value_beats_topic_and_global(self, profile_service):
        result = await profile_service.resolve(
            project=Project(
                topic="self_improvement",
                profile_overrides_json='{"duration_seconds": 60}',
            ),
            global_values={"default_duration": "30"},
        )
        assert result.duration_seconds.value == 60
        assert result.duration_seconds.source is ProfileSource.PROJECT

    async def test_topic_value_beats_global_when_project_is_inherited(self, profile_service):
        result = await profile_service.resolve(
            project=Project(topic="self_improvement"),
            global_values={"default_duration": "30"},
        )
        assert result.duration_seconds.source is ProfileSource.FORMAT
        assert result.duration_seconds.value == _BUILTIN_MIDPOINT

    async def test_global_value_beats_built_in(self, profile_service):
        result = await profile_service.resolve(
            project=Project(
                topic="self_improvement",
                profile_overrides_json='{"format_name": "no-such-format"}',
            ),
            global_values={"default_duration": "20"},
        )
        assert result.duration_seconds.value == 20.0
        assert result.duration_seconds.source is ProfileSource.GLOBAL

    async def test_built_in_midpoint_when_nothing_set(self, profile_service):
        result = await profile_service.resolve(
            project=Project(topic="psychology"),
            global_values={},
        )
        assert result.duration_seconds.value == _BUILTIN_MIDPOINT
        assert result.duration_seconds.source is ProfileSource.FORMAT


class TestProjectProfileReset:
    async def test_reset_returns_clean_project_json(self, profile_service):
        project = Project(
            topic="self_improvement",
            profile_overrides_json='{"duration_seconds": 60, "caption_style": "plain"}',
        )
        updated = await profile_service.reset_override(project, "duration_seconds")
        assert json.loads(updated.profile_overrides_json) == {"caption_style": "plain"}

    async def test_reset_unknown_key_leaves_project_untouched(self, profile_service):
        project = Project(topic="self_improvement")
        updated = await profile_service.reset_override(project, "no_such_field")
        assert json.loads(updated.profile_overrides_json) == {}

    async def test_reset_does_not_mutate_original(self, profile_service):
        project = Project(
            topic="self_improvement",
            profile_overrides_json='{"duration_seconds": 60}',
        )
        await profile_service.reset_override(project, "duration_seconds")
        assert json.loads(project.profile_overrides_json) == {"duration_seconds": 60}


class TestProjectProfileGlobalAndDefaultTiers:
    async def test_caption_style_project_beats_global(self, profile_service):
        result = await profile_service.resolve(
            project=Project(
                topic="self_improvement",
                profile_overrides_json='{"caption_style": "plain"}',
            ),
            global_values={"default_caption_style": "highlight"},
        )
        assert result.caption_style.value == "plain"
        assert result.caption_style.source is ProfileSource.PROJECT

    async def test_format_default_beats_global_default(self, profile_service):
        result = await profile_service.resolve(
            project=Project(topic="self_improvement"),
            global_values={"default_caption_style": "plain"},
        )
        assert result.caption_style.value == "highlight"
        assert result.caption_style.source is ProfileSource.BUILT_IN

    async def test_format_default_caption_style_tier(self, profile_service, monkeypatch):
        from shorts_creator.formats import base as formats_base

        listy = formats_base.FormatDefinition.from_dict(
            {
                "name": "listy",
                "label": "Listy",
                "caption_styles": ["highlight", "list"],
                "default_caption_style": "list",
            }
        )

        class _FakeRegistry:
            def get(self, name):
                return listy if name == "listy" else None

            def has(self, name):
                return name == "listy"

        monkeypatch.setattr(
            "shorts_creator.services.project_profile_service.format_registry",
            _FakeRegistry(),
        )
        result = await profile_service.resolve(
            project=Project(
                topic="self_improvement",
                profile_overrides_json='{"format_name": "listy"}',
            ),
            global_values={"default_caption_style": "highlight"},
        )
        assert result.caption_style.value == "list"
        assert result.caption_style.source is ProfileSource.BUILT_IN

    async def test_styleless_format_stray_override_stays_empty(self, profile_service):
        result = await profile_service.resolve(
            project=Project(
                topic="self_improvement",
                profile_overrides_json=('{"format_name": "topn", "caption_style": "highlight"}'),
            ),
            global_values={},
        )
        assert result.caption_style.value == ""
        issues = await profile_service.validate_pair_for_project(
            Project(
                topic="self_improvement",
                profile_overrides_json=('{"format_name": "topn", "caption_style": "highlight"}'),
            )
        )
        assert all(i.code != "REQ_STYLE" for i in issues)

    async def test_invalid_style_on_styled_format_still_rejected(self, profile_service):
        issues = await profile_service.validate_pair_for_project(
            Project(
                topic="self_improvement",
                profile_overrides_json='{"caption_style": "list"}',
            )
        )
        assert any(i.code == "REQ_STYLE" for i in issues)

    async def test_styleless_format_forces_empty_caption_style(self, profile_service):
        result = await profile_service.resolve(
            project=Project(
                topic="self_improvement",
                profile_overrides_json='{"format_name": "topn"}',
            ),
            global_values={},
        )
        assert result.caption_style.value == ""
        issues = await profile_service.validate_pair_for_project(
            Project(
                topic="self_improvement",
                profile_overrides_json='{"format_name": "topn"}',
            )
        )
        assert all(i.code != "REQ_STYLE" for i in issues)

    async def test_styleful_format_keeps_default_caption_style(self, profile_service):
        result = await profile_service.resolve(
            project=Project(topic="self_improvement"),
            global_values={},
        )
        assert result.caption_style.value == "highlight"

    async def test_duration_global_values_apply(self, profile_service):
        result = await profile_service.resolve(
            project=Project(
                topic="self_improvement",
                profile_overrides_json='{"format_name": "no-such-format"}',
            ),
            global_values={"default_duration": "42"},
        )
        assert result.duration_seconds.value == 42.0
        assert result.duration_seconds.source is ProfileSource.GLOBAL

    async def test_duration_builtin_default_when_nothing_set(self, profile_service):
        result = await profile_service.resolve(
            project=Project(
                topic="self_improvement",
                profile_overrides_json='{"format_name": "no-such-format"}',
            ),
            global_values={},
        )
        assert result.duration_seconds.value == 30.0
        assert result.duration_seconds.source is ProfileSource.BUILT_IN

    async def test_asset_project_beats_global_default(self, profile_service):
        result = await profile_service.resolve(
            project=Project(
                topic="self_improvement",
                profile_overrides_json='{"asset_music_id": "proj-music"}',
            ),
            global_values={"asset_default_music_id": "glob-music"},
        )
        assert result.asset_music_id.value == "proj-music"
        assert result.asset_music_id.source is ProfileSource.PROJECT

    async def test_asset_global_default_applies(self, profile_service):
        result = await profile_service.resolve(
            project=Project(topic="self_improvement"),
            global_values={"asset_default_font_id": "glob-font"},
        )
        assert result.asset_font_id.value == "glob-font"
        assert result.asset_font_id.source is ProfileSource.GLOBAL

    async def test_assets_none_when_not_configured(self, profile_service):
        result = await profile_service.resolve(
            project=Project(topic="self_improvement"),
            global_values={},
        )
        assert result.asset_music_id.value is None
        assert result.asset_font_id.value is None
        assert result.asset_bg_clip_id.value is None
        assert result.asset_outro_clip_id.value is None
        assert result.asset_watermark_id.value is None
        assert result.asset_music_id.source is ProfileSource.BUILT_IN


class TestProjectProfileFixedFields:
    async def test_format_name_defaults_to_narrated(self, profile_service):
        result = await profile_service.resolve(
            project=Project(topic="self_improvement"),
            global_values={},
        )
        assert result.format_name.value == "narrated"
        assert result.format_name.source is ProfileSource.BUILT_IN

    async def test_format_name_project_override_applies(self, profile_service):
        result = await profile_service.resolve(
            project=Project(
                topic="self_improvement",
                profile_overrides_json='{"format_name": "narrated"}',
            ),
            global_values={},
        )
        assert result.format_name.value == "narrated"
        assert result.format_name.source is ProfileSource.PROJECT

    async def test_topic_resolved_from_project_topic(self, profile_service):
        result = await profile_service.resolve(
            project=Project(topic="psychology"),
            global_values={},
        )
        assert result.topic.value == "psychology"

    async def test_reel_size_is_global_only_config_value(self, profile_service):
        result = await profile_service.resolve(
            project=Project(topic="self_improvement"),
            global_values={"reel_width": "9999", "reel_height": "1111"},
        )
        assert result.reel_width.value == 1080
        assert result.reel_height.value == 1920
        assert result.reel_width.source is ProfileSource.BUILT_IN
        assert result.reel_height.source is ProfileSource.BUILT_IN


class TestProjectProfileResolutionDetails:
    async def test_is_overridden_only_true_for_project_source(self, profile_service):
        project_result = await profile_service.resolve(
            project=Project(
                topic="self_improvement",
                profile_overrides_json='{"duration_seconds": 60}',
            ),
            global_values={},
        )
        assert project_result.duration_seconds.is_overridden is True

        inherited_result = await profile_service.resolve(
            project=Project(topic="self_improvement"),
            global_values={"default_duration": "30"},
        )
        assert inherited_result.duration_seconds.is_overridden is False
        assert inherited_result.caption_style.is_overridden is False

    async def test_snapshot_dict_is_json_safe(self, profile_service):
        result = await profile_service.resolve(
            project=Project(topic="self_improvement"),
            global_values={"default_duration": "30"},
        )
        snapshot = result.snapshot_dict()
        assert json.loads(json.dumps(snapshot)) == snapshot
        assert snapshot["duration_seconds"] is not None

    async def test_global_duration_can_be_int(self, profile_service):
        result = await profile_service.resolve(
            project=Project(
                topic="self_improvement",
                profile_overrides_json='{"format_name": "no-such-format"}',
            ),
            global_values={"default_duration": "20"},
        )
        assert result.duration_seconds.value == 20.0

    async def test_garbage_global_duration_falls_back_to_format(self, profile_service):
        result = await profile_service.resolve(
            project=Project(topic="self_improvement"),
            global_values={"default_duration": "not-a-float"},
        )
        assert result.duration_seconds.source is ProfileSource.FORMAT


class _StubGlobalStore:
    def __init__(self, values):
        self._values = values

    async def get_global_values(self):
        return self._values


class TestProjectProfileGlobalStore:
    async def test_resolve_reads_global_store_when_no_values_passed(self):
        service = ProjectProfileService(
            config=CONFIG,
            global_store=_StubGlobalStore({"default_duration": "20"}),
        )
        result = await service.resolve(
            Project(
                topic="self_improvement",
                profile_overrides_json='{"format_name": "no-such-format"}',
            )
        )
        assert result.duration_seconds.value == 20.0
        assert result.duration_seconds.source is ProfileSource.GLOBAL
