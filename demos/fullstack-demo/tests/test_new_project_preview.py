"""Composer "Stages" group markup (gap F1): the `new-project-stages` strip
renders the four stage toggles (music/outro/watermark/background) with
checked state resolved from the profile the same way syncComposerHidden
computes the untouched payload: the resolved stages overlay the composer
defaults, then the rank-format forcing pins music on — so the checkbox
state always matches what the JS would submit without user interaction.
"""

import json
import re

from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProfileSource,
    ResolvedSetting,
)
from shorts_creator.ui.pages.new_project import new_project_form, project_settings_form

_STAGE_KEYS = ("music", "outro", "watermark", "background")

_DEFAULTS = {
    "music": False,
    "outro": True,
    "watermark": False,
    "background": True,
}

_TOGGLE_RE = re.compile(
    r'<input type="checkbox" data-stage="([a-z]+)"( checked)?'
    r' class="accent-primary stage-toggle"'
)


class _Project:
    id = "p1"
    title = "My Short"


def _resolved(value, source):
    return ResolvedSetting(
        value=value, source=source, is_overridden=source is ProfileSource.PROJECT
    )


def _settings_profile(**extra) -> EffectiveProjectProfile:
    data = {
        "topic": _resolved("self_improvement", ProfileSource.GLOBAL),
        "format_name": _resolved("narrated", ProfileSource.BUILT_IN),
        "duration_seconds": _resolved(30, ProfileSource.GLOBAL),
        "caption_style": _resolved("highlight", ProfileSource.BUILT_IN),
        "asset_music_id": _resolved(None, ProfileSource.BUILT_IN),
        "asset_font_id": _resolved(None, ProfileSource.BUILT_IN),
        "asset_bg_clip_id": _resolved(None, ProfileSource.BUILT_IN),
        "asset_outro_clip_id": _resolved(None, ProfileSource.BUILT_IN),
        "asset_watermark_id": _resolved(None, ProfileSource.BUILT_IN),
        "bg_mode": _resolved(None, ProfileSource.BUILT_IN),
    }
    data.update(extra)
    return EffectiveProjectProfile(**data)


def _asset_options():
    return {
        "music": [("m1", "Lo-fi")],
        "font": [("f1", "Inter")],
        "bg_clip": [("bg1", "City")],
        "outro_clip": [("o1", "Outro")],
        "watermark": [("w1", "Mark")],
    }


def _settings_html(profile):
    return str(project_settings_form(_Project(), profile, _asset_options()))


def _toggles(html: str) -> dict:
    """data-stage -> checked state of the four stage toggles in the markup."""
    return {key: bool(flag) for key, flag in _TOGGLE_RE.findall(html)}


def _declared_stages(html: str):
    seg = html.split('id="new-project-stages-json"')[1].split(">")[0]
    match = re.search(r'value="([^"]*)"', seg)
    if not match:
        return None
    return json.loads(match.group(1).replace("&quot;", '"')) if match.group(1) else None


class TestStageTogglesMarkup:
    def test_settings_form_overridden_stages_profile_checks_the_toggles(self):
        profile = _settings_profile(
            stages=_resolved(
                {"music": True, "outro": False, "watermark": True, "background": False},
                ProfileSource.PROJECT,
            ),
        )
        html = _settings_html(profile)
        assert _toggles(html) == {
            "music": True,
            "outro": False,
            "watermark": True,
            "background": False,
        }
        assert _declared_stages(html) == {
            "music": True,
            "outro": False,
            "watermark": True,
            "background": False,
        }

    def test_settings_form_overridden_outro_false_unchecks_outro_only(self):
        profile = _settings_profile(
            stages=_resolved({**_DEFAULTS, "outro": False}, ProfileSource.PROJECT),
        )
        html = _settings_html(profile)
        assert _toggles(html) == {**_DEFAULTS, "outro": False}

    def test_settings_form_rank_format_forces_music_checked_on_default_profile(self):
        profile = _settings_profile(format_name=_resolved("topn", ProfileSource.GLOBAL))
        html = _settings_html(profile)
        toggles = _toggles(html)
        assert toggles == {**_DEFAULTS, "music": True}
        assert "data-stages=" not in html  # declared contract unchanged: unforced

    def test_settings_form_rank_format_keeps_declared_stages_unforced(self):
        profile = _settings_profile(
            format_name=_resolved("topn", ProfileSource.GLOBAL),
            stages=_resolved(
                {"music": False, "outro": True, "watermark": False, "background": True},
                ProfileSource.PROJECT,
            ),
        )
        html = _settings_html(profile)
        assert 'data-stages="{&quot;music&quot;: false' in html  # declared stays as the override
        assert _declared_stages(html) == {
            "music": False,
            "outro": True,
            "watermark": False,
            "background": True,
        }
        assert _toggles(html)["music"] is True  # forcing is the rendered default

    def test_create_form_renders_default_stage_toggles(self):
        html = str(new_project_form())
        assert _toggles(html) == _DEFAULTS
        assert "data-stages=" not in html

    def test_stage_toggles_carry_labels_and_data_stage_keys(self):
        profile = _settings_profile()
        html = _settings_html(profile)
        for key, label in (
            ("music", "Music"),
            ("outro", "Outro"),
            ("watermark", "Watermark"),
            ("background", "Background"),
        ):
            assert f'data-stage="{key}"' in html
            seg = html.split(f'data-stage="{key}"')[1].split("</label>")[0]
            assert label in seg, f"{key} toggle missing {label!r} label"


class TestBgModeControl:
    """The media panel's Background Video/Image radio pair defaults to video,
    prefills from a bg_mode override, and hides the Stock source in image mode."""

    def test_settings_form_defaults_to_video_with_stock_source(self):
        html = _settings_html(_settings_profile())
        assert 'name="bg_mode"' in html
        assert 'value="video" checked' in html
        assert 'id="bg-clip-picker-wrapper"' in html
        assert "Background clip" in html
        assert ">Stock clip<" in html

    def test_settings_form_image_override_checks_image_and_hides_stock(self):
        html = _settings_html(_settings_profile(bg_mode=_resolved("image", ProfileSource.PROJECT)))
        assert 'value="image" checked' in html
        assert 'id="bg-clip-picker-wrapper"' in html
        assert "Background image" in html
        assert ">Stock clip<" not in html
