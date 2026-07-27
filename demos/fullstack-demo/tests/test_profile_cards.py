from html import escape
from types import SimpleNamespace

from shorts_creator.controllers.projects import _profile_card
from shorts_creator.formats import registry as formats
from shorts_creator.models.project import Project
from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProfileSource,
    ResolvedSetting,
)
from shorts_creator.ui.components.project_tabs import project_header
from shorts_creator.ui.components.settings_profile import caption_style_label
from shorts_creator.ui.pages.new_project import _profile_strip


def _rsetting(value, source=ProfileSource.PROJECT):
    return ResolvedSetting(
        value=value, source=source, is_overridden=source is ProfileSource.PROJECT
    )


def _profile(**kw):
    defaults = {
        "duration_seconds": 40,
        "format_name": "topn",
        "caption_style": "",
        "reel_width": 1080,
        "reel_height": 1920,
    }
    defaults.update(kw)
    return EffectiveProjectProfile(**defaults)


def _project(overrides_json="{}"):
    return SimpleNamespace(id="p1", profile_overrides_json=overrides_json)


class TestCaptionStyleLabel:
    def test_ranked_format_empty_value_means_per_item_screens(self):
        assert caption_style_label(formats.get("topn"), "") == "Per-item screens"

    def test_ranked_format_list_value(self):
        assert caption_style_label(formats.get("topn"), "list") == "List"

    def test_narrated_highlight_label(self):
        assert (
            caption_style_label(formats.get("narrated"), "highlight") == "Highlight (word-by-word)"
        )

    def test_narrated_plain_label(self):
        assert caption_style_label(formats.get("narrated"), "plain") == "Plain (static lines)"

    def test_unknown_value_passes_through(self):
        assert caption_style_label(formats.get("topn"), "fancy") == "fancy"

    def test_no_format_no_value(self):
        assert caption_style_label(None, "") is None

    def test_empty_for_narrated_means_default_highlight(self):
        assert caption_style_label(formats.get("narrated"), "") == "Highlight (word-by-word)"


class TestProfileCardHtml:
    def test_row_markup_is_not_double_escaped(self):
        html = str(_profile_card(_project(), _profile(), {}))
        assert "&lt;div" not in html
        assert "&amp;lt;div" not in html
        assert '<div class="flex items-center justify-between gap-3 py-1.5' in html
        assert "Duration" in html
        assert "40s" in html

    def test_caption_style_row_shows_per_item_screens_label(self):
        html = str(_profile_card(_project(), _profile(), {}))
        assert ">Per-item screens<" in html
        assert ">topn<" in html

    def test_caption_style_row_shows_list_label(self):
        html = str(_profile_card(_project(), _profile(caption_style="list"), {}))
        assert ">List<" in html

    def test_music_row_uses_asset_name(self):
        project = _project()
        profile = _profile(asset_music_id=_rsetting("m-uuid"))
        html = str(
            _profile_card(
                project,
                profile,
                {"music": [("m-uuid", "My Track")]},
            )
        )
        assert ">My Track<" in html
        assert "m-uuid" not in html

    def test_asset_rows_show_resolved_names_for_all_five_roles(self):
        profile = _profile(
            asset_music_id=_rsetting("m-uuid"),
            asset_font_id=_rsetting("f-uuid"),
            asset_bg_clip_id=_rsetting("b-uuid"),
            asset_outro_clip_id=_rsetting("o-uuid"),
            asset_watermark_id=_rsetting("w-uuid"),
        )
        html = str(
            _profile_card(
                _project(),
                profile,
                {
                    "music": [("m-uuid", "My Track")],
                    "font": [("f-uuid", "Mono Font")],
                    "bg_clip": [("b-uuid", "City B-roll")],
                    "outro_clip": [("o-uuid", "End Card")],
                    "watermark": [("w-uuid", "Logo")],
                },
            )
        )
        for name in ("My Track", "Mono Font", "City B-roll", "End Card", "Logo"):
            assert f">{name}<" in html

    def test_overridden_asset_row_carries_reset_button(self):
        profile = _profile(
            asset_music_id=_rsetting("m-uuid"),
            asset_font_id=_rsetting("f-uuid", source=ProfileSource.BUILT_IN),
        )
        html = str(_profile_card(_project(), profile, {"music": [("m-uuid", "My Track")]}))
        assert (
            'data-override-toggle data-key="asset_music_id"'
            ' data-reset-url="/api/projects/p1/reset-override"'
        ) in html
        assert ">Reset<" in html
        assert 'data-key="asset_font_id"' not in html

    def test_asset_rows_show_source_badges(self):
        profile = _profile(
            asset_music_id=_rsetting("m-uuid"),
            asset_bg_clip_id=_rsetting("b-uuid", source=ProfileSource.GLOBAL),
        )
        html = str(
            _profile_card(
                _project(),
                profile,
                {"music": [("m-uuid", "My Track")], "bg_clip": [("b-uuid", "B")]},
            )
        )
        assert 'data-source="project"' in html
        assert "Project override" in html
        assert 'data-source="global"' in html
        assert "Global Default" in html

    def test_non_overridden_asset_row_shows_builtin_badge_without_reset(self):
        profile = _profile(asset_music_id=_rsetting("m-uuid", source=ProfileSource.BUILT_IN))
        html = str(_profile_card(_project(), profile, {"music": [("m-uuid", "My Track")]}))
        assert "Built-in" in html
        assert "Reset" not in html

    def test_card_ignores_stale_raw_override_without_resolved_setting(self):
        project = _project('{"asset_music_id": "stale-uuid"}')
        html = str(_profile_card(project, _profile(), {}))
        assert "stale-uuid" not in html
        assert "Music" not in html

    def test_phase2_rows_show_resolved_values_with_reset_buttons(self):
        profile = _profile(
            stage_accents=_rsetting({"message": "0x22D3EEFF"}),
            section_holds=_rsetting({"message": 1.5}),
            loudness_target_lufs=_rsetting(-12.0),
            audio_normalize=_rsetting(False),
        )
        html = str(_profile_card(_project(), profile, {}))
        for key in (
            "stage_accents",
            "section_holds",
            "loudness_target_lufs",
            "audio_normalize",
        ):
            assert f'data-key="{key}"' in html
            assert 'data-reset-url="/api/projects/p1/reset-override"' in html
        assert escape('{"message": "0x22D3EEFF"}') in html
        assert "1.5" in html
        assert "-12" in html
        assert ">False<" in html


class TestProfileStripHtml:
    def test_strip_is_not_double_escaped(self):
        html = str(_profile_strip(_profile()))
        assert "&lt;div" not in html
        assert "Per-item screens" in html

    def test_strip_rows_show_list_label(self):
        html = str(_profile_strip(_profile(caption_style="list")))
        assert ">List<" in html


class TestProjectHeaderStyleBadge:
    def _header(self, overrides):
        return str(
            project_header(
                Project(
                    id="p1",
                    topic="t",
                    title="T",
                    profile_overrides_json=str(overrides).replace("'", '"')
                    if isinstance(overrides, str)
                    else __import__("json").dumps(overrides or {}),
                )
            )
        )

    def test_topn_default_shows_no_caption_badge(self):
        html = self._header({"format_name": "topn"})
        assert "Highlight" not in html
        assert "Per-item screens" not in html

    def test_narrated_default_shows_no_caption_badge(self):
        html = self._header({"format_name": "narrated"})
        assert "Highlight" not in html

    def test_explicit_list_value_shows_list_badge(self):
        html = self._header({"format_name": "topn", "caption_style": "list"})
        assert ">List<" in html

    def test_explicit_plain_value_shows_plain_badge(self):
        html = self._header({"format_name": "narrated", "caption_style": "plain"})
        assert ">Plain (static lines)<" in html
