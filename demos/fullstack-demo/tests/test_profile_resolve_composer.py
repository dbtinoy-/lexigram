"""Composer fields resolve through the four-tier profile service."""

import pytest

from shorts_creator.models.project import Project
from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProfileSource,
    ProjectProfileOverrides,
    ResolvedSetting,
)
from shorts_creator.services.core import AppConfig
from shorts_creator.services.project_profile_service import ProjectProfileService


class _Store:
    def __init__(self, values=None):
        self._values = values or {}

    async def get_global_values(self):
        return dict(self._values)


@pytest.fixture
async def service():
    yield ProjectProfileService(AppConfig(), _Store())


async def test_composer_fields_resolve_from_project_overrides(service):
    project = Project(
        topic="self_improvement",
        profile_overrides_json=ProjectProfileOverrides(
            pacing_wps=2.7,
            hook_text="Custom hook",
            outro_text="See you next time",
            sections=["message", "metaphor"],
            style={
                "chunk_size": 2,
                "caption_font_size": 68,
                "caption_outline_width": 4,
            },
            layout={"anchor": "lower_third", "block_width_pct": 70},
            stages={"music": True},
        ).model_dump_json(),
    )
    profile = await service.resolve(project)
    assert profile.pacing_wps.value == 2.7
    assert profile.pacing_wps.source is ProfileSource.PROJECT
    assert profile.hook_text.value == "Custom hook"
    assert profile.outro_text.value == "See you next time"
    assert profile.outro_text.source is ProfileSource.PROJECT
    assert profile.sections.value == ["message", "metaphor"]
    assert profile.style.value == {
        "chunk_size": 2,
        "caption_font_size": 68,
        "caption_outline_width": 4,
    }
    assert profile.stages.value == {
        "music": True,
        "outro": True,
        "watermark": False,
        "background": True,
    }


async def test_layout_clamped_to_format_slider_range(service):
    project = Project(
        topic="self_improvement",
        profile_overrides_json=ProjectProfileOverrides(
            layout={"block_width_pct": 99, "numbered_scale": 9.0},
        ).model_dump_json(),
    )
    profile = await service.resolve(project)
    assert profile.layout.value["block_width_pct"] == 95  # narrated declares [60, 95]
    assert profile.layout.value["numbered_scale"] == 2.5  # declared [1.2, 2.5]


async def test_voice_fields_resolve_from_project_overrides(service):
    project = Project(
        topic="self_improvement",
        profile_overrides_json=ProjectProfileOverrides(
            audience_persona="busy founders",
            banned_topics=["politics", "get-rich schemes"],
            tone_rules=["no jargon", "short sentences"],
            voice_preset="dramatic",
            hook_lead_in_seconds=1.5,
        ).model_dump_json(),
    )
    profile = await service.resolve(project)
    assert profile.audience_persona.value == "busy founders"
    assert profile.audience_persona.source is ProfileSource.PROJECT
    assert profile.banned_topics.value == ["politics", "get-rich schemes"]
    assert profile.tone_rules.value == ["no jargon", "short sentences"]
    assert profile.voice_preset.value == "dramatic"
    assert profile.hook_lead_in_seconds.value == 1.5


async def test_voice_fields_clamp_and_default(service):
    project = Project(
        topic="self_improvement",
        profile_overrides_json=ProjectProfileOverrides(
            hook_lead_in_seconds=9.0,
        ).model_dump_json(),
    )
    profile = await service.resolve(project)
    assert profile.hook_lead_in_seconds.value == 3.0
    assert profile.voice_preset.value is None
    assert profile.audience_persona.value is None
    assert profile.banned_topics.value is None
    assert profile.tone_rules.value is None


async def test_bg_mode_resolves_from_project_overrides(service):
    project = Project(
        topic="self_improvement",
        profile_overrides_json=ProjectProfileOverrides(bg_mode="image").model_dump_json(),
    )
    profile = await service.resolve(project)
    assert profile.bg_mode.value == "image"
    assert profile.bg_mode.source is ProfileSource.PROJECT
    assert profile.bg_mode.is_overridden


async def test_composer_fields_default_to_none(service):
    profile = await service.resolve(Project(topic="self_improvement"))
    assert profile.pacing_wps.value is None
    assert profile.hook_text.value is None
    assert profile.outro_text.value is None
    assert profile.sections.value is None
    assert profile.style.value is None
    assert profile.layout.value is None
    assert profile.stages.source is ProfileSource.FORMAT
    assert profile.stages.value == {
        "music": True,
        "outro": True,
        "watermark": False,
        "background": True,
    }
    assert profile.bg_mode.value is None


def test_snapshot_omits_unset_composer_fields():
    profile = EffectiveProjectProfile(
        duration_seconds=ResolvedSetting(45, ProfileSource.PROJECT, True),
        caption_style=ResolvedSetting("highlight", ProfileSource.FORMAT, False),
    )
    snap = profile.snapshot_dict()
    assert snap["duration_seconds"] == 45
    for name in (
        "layout",
        "palette",
        "style",
        "sections",
        "section_texts",
        "stages",
        "pacing_wps",
        "hook_text",
        "outro_text",
        "voice_preset",
        "hook_lead_in_seconds",
        "audience_persona",
        "banned_topics",
        "tone_rules",
    ):
        assert name not in snap


def test_snapshot_includes_set_composer_fields():
    profile = EffectiveProjectProfile(
        duration_seconds=ResolvedSetting(45, ProfileSource.PROJECT, True),
        layout=ResolvedSetting({"anchor": "lower_third"}, ProfileSource.PROJECT, True),
        stages=ResolvedSetting({"music": True}, ProfileSource.PROJECT, True),
        outro_text=ResolvedSetting("See you next time", ProfileSource.PROJECT, True),
        voice_preset=ResolvedSetting("dramatic", ProfileSource.PROJECT, True),
        hook_lead_in_seconds=ResolvedSetting(1.5, ProfileSource.PROJECT, True),
        audience_persona=ResolvedSetting("busy founders", ProfileSource.PROJECT, True),
    )
    snap = profile.snapshot_dict()
    assert snap["layout"] == {"anchor": "lower_third"}
    assert snap["stages"] == {"music": True}
    assert snap["outro_text"] == "See you next time"
    assert snap["voice_preset"] == "dramatic"
    assert snap["hook_lead_in_seconds"] == 1.5
    assert snap["audience_persona"] == "busy founders"
