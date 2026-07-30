"""Untouched composer JSON composites must not become project overrides.

Regression tests for gap A1: fresh projects (no inherited profile) and
projects whose inherited (Topic/Global) style differs from the composer's
built-in defaults were silently persisting style/palette/layout/stages/
sections overrides the user never touched, reversing provenance and
drifting from what the settings page resolves.

Payloads mirror what syncComposerHidden (composer-preview.js:762-823)
really submits: every widget is rendered and read unconditionally, so a
submission always carries the full widget key set (style's 5 keys,
layout's ~10 keys, the colour widgets' 0xrrggbbFF round-trip form).
"""

import json
import re

from shorts_creator.ui.pages.new_project import form_overrides

STYLE_FULL = {
    "chunk_size": 3,
    "caption_font_size": 56,
    "caption_outline_width": 2,
    "uppercase": False,
    "scrim_alpha": 0,
}

LAYOUT_FULL = {
    "anchor": "center",
    "block_width_pct": 80,
    "numbered_scale": 1.6,
    "pill_per_word": True,
    "watermark_corner": "bottom_right",
    "watermark_size_pct": 10,
    "watermark_opacity": 0.85,
    "music_volume": 0.2,
    "music_fade_seconds": 2.0,
    "fade_out_seconds": 1.0,
}

PALETTE_FULL = {
    "highlight_colour": "0x7c5cfaFF",
    "pill_bg_colour": "0x000000FF",
}

STAGES_FULL = {
    "music": False,
    "outro": True,
    "watermark": False,
    "background": True,
}


class _Setting:
    def __init__(self, value, is_overridden=False):
        self.value = value
        self.is_overridden = is_overridden


class _StubProfile:
    def __init__(self, **settings):
        for key, value in settings.items():
            if not isinstance(value, _Setting):
                value = _Setting(value)
            setattr(self, key, value)


def _submitted(**overrides):
    data = {
        "format": "narrated",
        "type": "self_improvement",
        "style": json.dumps(STYLE_FULL),
        "layout": json.dumps(LAYOUT_FULL),
        "palette": json.dumps(PALETTE_FULL),
        "stages": json.dumps(STAGES_FULL),
    }
    data.update(overrides)
    return data


class TestUntouchedComposerJSON:
    def test_fresh_project_full_widget_payloads_are_not_persisted(self):
        overrides = form_overrides(_submitted(), profile=None)
        for key in ("style", "palette", "layout", "stages"):
            assert key not in overrides, f"{key} leaked as an override"


class TestBgMode:
    def test_bg_mode_image_persists_as_override(self):
        overrides = form_overrides(_submitted(bg_mode="image"), profile=_StubProfile())
        assert overrides["bg_mode"] == "image"

    def test_bg_mode_video_clears_override(self):
        overrides = form_overrides(_submitted(bg_mode="video"), profile=_StubProfile())
        assert overrides.get("bg_mode") == ""

    def test_bg_mode_absent_is_untouched(self):
        overrides = form_overrides(_submitted(), profile=_StubProfile())
        assert "bg_mode" not in overrides

    def test_bg_mode_image_with_assets_source_keeps_stock_cleared(self):
        overrides = form_overrides(
            _submitted(bg_mode="image", media_source_bg_clip="assets"),
            profile=_StubProfile(),
        )
        assert overrides["bg_mode"] == "image"
        assert overrides["bg_source"] == ""
        assert overrides["stock_provider"] == ""

    def test_inherited_partial_style_untouched_full_submission_is_neutral(self):
        profile = _StubProfile(style={"chunk_size": 5})
        data = _submitted(style=json.dumps({**STYLE_FULL, "chunk_size": 5}))
        overrides = form_overrides(data, profile=profile)
        assert "style" not in overrides

    def test_layout_extras_only_change_is_neutral_for_inherited_composite(self):
        profile = _StubProfile(layout={**LAYOUT_FULL, "music_volume": 0.3})
        data = _submitted(layout=json.dumps({**LAYOUT_FULL, "music_volume": 0.3}))
        overrides = form_overrides(data, profile=profile)
        assert "layout" not in overrides

    def test_palette_round_trip_untouched_against_inherited_palette(self):
        profile = _StubProfile(
            palette={"highlight_colour": "0x112233FF", "pill_bg_colour": "0x000000C0"}
        )
        data = _submitted(
            palette=json.dumps({"highlight_colour": "0x112233FF", "pill_bg_colour": "0x000000FF"})
        )
        overrides = form_overrides(data, profile=profile)
        assert "palette" not in overrides

    def test_stages_music_forced_for_rank_format_is_neutral(self):
        profile = _StubProfile(format_name="topn")
        data = _submitted(
            format="topn",
            stages=json.dumps({**STAGES_FULL, "music": True}),
        )
        overrides = form_overrides(data, profile=profile)
        assert "stages" not in overrides

    def test_sections_equal_to_topic_default_are_not_persisted(self):
        profile = _StubProfile(topic="self_improvement")
        data = _submitted(
            sections='["message", "metaphor"]',
            type="self_improvement",
        )
        overrides = form_overrides(data, profile=profile)
        assert "sections" not in overrides

    def test_restored_default_does_not_override_an_existing_override(self):
        profile = _StubProfile(
            style=_Setting(STYLE_FULL, is_overridden=True),
        )
        overrides = form_overrides(_submitted(), profile=profile)
        assert overrides.get("style") == STYLE_FULL


class TestChangedCompositesStillPersist:
    def test_style_change_persists(self):
        overrides = form_overrides(
            _submitted(style=json.dumps({**STYLE_FULL, "chunk_size": 7})),
            profile=None,
        )
        assert overrides.get("style") == {**STYLE_FULL, "chunk_size": 7}

    def test_layout_extras_only_change_persists(self):
        overrides = form_overrides(
            _submitted(layout=json.dumps({**LAYOUT_FULL, "music_volume": 0.3})),
            profile=None,
        )
        assert overrides.get("layout") == {**LAYOUT_FULL, "music_volume": 0.3}

    def test_user_palette_persists(self):
        overrides = form_overrides(
            _submitted(
                palette=json.dumps(
                    {"highlight_colour": "0x112233FF", "pill_bg_colour": "0x000000FF"}
                )
            ),
            profile=None,
        )
        assert overrides["palette"]["highlight_colour"] == "0x112233FF"

    def test_stage_toggle_persists(self):
        overrides = form_overrides(
            _submitted(
                stages=json.dumps({**STAGES_FULL, "outro": False}),
            ),
            profile=None,
        )
        assert overrides.get("stages", {}).get("outro") is False

    def test_user_unchecked_rank_music_persists(self):
        """Gap F1: the rank forcing is a default, not a cap — a user
        unchecking music on a rank format submits music:false, which must
        persist (it differs from the forced neutral)."""
        overrides = form_overrides(
            _submitted(
                format="topn",
                stages=json.dumps({**STAGES_FULL, "music": False}),
            ),
            profile=_StubProfile(format_name="topn"),
        )
        assert overrides.get("stages", {}).get("music") is False

    def test_custom_sections_persist(self):
        overrides = form_overrides(
            _submitted(sections='["message", "metaphor", "hook", "top_items"]'),
            profile=None,
        )
        assert overrides.get("sections") == ["message", "metaphor", "hook", "top_items"]


class TestBlankClearsComposerOverrides:
    def test_blank_hook_text_clears_override(self):
        profile = _StubProfile(hook_text=_Setting("Catchy hook", is_overridden=True))
        overrides = form_overrides({**_submitted(), "hook_text": ""}, profile=profile)
        assert overrides.get("hook_text") == ""

    def test_blank_hook_text_without_override_does_nothing(self):
        overrides = form_overrides({**_submitted(), "hook_text": ""}, profile=None)
        assert "hook_text" not in overrides

    def test_blank_outro_text_clears_override(self):
        profile = _StubProfile(outro_text=_Setting("See you", is_overridden=True))
        overrides = form_overrides({**_submitted(), "outro_text": ""}, profile=profile)
        assert overrides.get("outro_text") == ""

    def test_blank_pacing_clears_override(self):
        profile = _StubProfile(pacing_wps=_Setting(2.5, is_overridden=True))
        overrides = form_overrides({**_submitted(), "pacing_wps": ""}, profile=profile)
        assert overrides.get("pacing_wps") == ""

    def test_new_hook_text_overrides_old(self):
        profile = _StubProfile(hook_text=_Setting("Old", is_overridden=True))
        overrides = form_overrides({**_submitted(), "hook_text": "New"}, profile=profile)
        assert overrides.get("hook_text") == "New"


class TestCaptionStyleClearing:
    def test_blank_caption_style_clears_stale_override(self):
        profile = _StubProfile(caption_style=_Setting("highlight", is_overridden=True))
        overrides = form_overrides({**_submitted(), "caption_style": ""}, profile=profile)
        assert overrides.get("caption_style") == ""

    def test_blank_caption_style_without_override_does_nothing(self):
        overrides = form_overrides({**_submitted(), "caption_style": ""}, profile=None)
        assert "caption_style" not in overrides

    def test_captionless_format_wizard_emits_clearing_input(self, monkeypatch):
        import shorts_creator.ui.pages.new_project as np

        monkeypatch.setattr(
            "shorts_creator.ui.pages.new_project_wizard._caption_field_data", lambda fmt: None
        )
        profile = _StubProfile(format_name="narrated")
        markup = str(np._wizard_caption_field(profile))
        assert 'name="caption_style"' in markup
        assert 'value=""' in markup


class TestPhase2BlankClearsOverrides:
    """Gap E2: a phase-2 knob returned to neutral submits '' and must clear a
    stored override (so the pop-on-empty save path removes it), instead of
    being skipped while the stale override survives."""

    def test_blank_audio_normalize_clears_override(self):
        profile = _StubProfile(audio_normalize=_Setting(False, is_overridden=True))
        overrides = form_overrides({**_submitted(), "audio_normalize": ""}, profile=profile)
        assert overrides.get("audio_normalize") == ""

    def test_blank_loudness_target_lufs_clears_override(self):
        profile = _StubProfile(loudness_target_lufs=_Setting(-12.0, is_overridden=True))
        overrides = form_overrides({**_submitted(), "loudness_target_lufs": ""}, profile=profile)
        assert overrides.get("loudness_target_lufs") == ""

    def test_blank_section_holds_clears_override(self):
        profile = _StubProfile(section_holds=_Setting({"message": 1.5}, is_overridden=True))
        overrides = form_overrides({**_submitted(), "section_holds": ""}, profile=profile)
        assert overrides.get("section_holds") == ""

    def test_blank_stage_accents_clears_override(self):
        profile = _StubProfile(
            stage_accents=_Setting({"message": "0x22D3EEFF"}, is_overridden=True)
        )
        overrides = form_overrides({**_submitted(), "stage_accents": ""}, profile=profile)
        assert overrides.get("stage_accents") == ""

    def test_absent_phase2_key_clears_nothing(self):
        profile = _StubProfile(
            audio_normalize=_Setting(False, is_overridden=True),
            loudness_target_lufs=_Setting(-12.0, is_overridden=True),
            section_holds=_Setting({"message": 1.5}, is_overridden=True),
            stage_accents=_Setting({"message": "0x22D3EEFF"}, is_overridden=True),
        )
        overrides = form_overrides(_submitted(), profile=profile)
        for key in ("audio_normalize", "loudness_target_lufs", "section_holds", "stage_accents"):
            assert key not in overrides

    def test_blank_without_override_creates_no_entry(self):
        data = {
            **_submitted(),
            "audio_normalize": "",
            "loudness_target_lufs": "",
            "section_holds": "",
            "stage_accents": "",
        }
        overrides = form_overrides(data, profile=None)
        for key in ("audio_normalize", "loudness_target_lufs", "section_holds", "stage_accents"):
            assert key not in overrides

    def test_blank_inherited_not_overridden_creates_no_entry(self):
        profile = _StubProfile(section_holds={"message": 1.5})
        overrides = form_overrides({**_submitted(), "section_holds": ""}, profile=profile)
        assert "section_holds" not in overrides

    def test_non_empty_phase2_values_still_persist(self):
        overrides = form_overrides(
            _submitted(
                background_motion="zoom",
                emphasis_style="off",
                loudness_target_lufs="-16",
                audio_normalize="false",
                section_holds='{"hook": 0.4, "message": 0.8, "conclusion": 0.3}',
                stage_accents='{"message": "0x22D3EEFF"}',
            ),
            profile=None,
        )
        assert overrides["background_motion"] == "zoom"
        assert overrides["emphasis_style"] == "off"
        assert overrides["loudness_target_lufs"] == -16.0
        assert overrides["audio_normalize"] is False
        assert overrides["section_holds"] == {"hook": 0.4, "message": 0.8, "conclusion": 0.3}
        assert overrides["stage_accents"] == {"message": "0x22D3EEFF"}


class TestAssetAutoClearsOverrides:
    """Gap E3(a): the asset selects' Auto option (value "") must clear a
    stored asset override and its paired media URL override through the
    pop-on-empty save path, instead of being skipped while the stale
    override survives."""

    def test_auto_clears_overridden_asset_and_paired_url(self):
        profile = _StubProfile(
            asset_music_id=_Setting("m-uuid", is_overridden=True),
            media_url_music=_Setting("http://m", is_overridden=True),
        )
        overrides = form_overrides(
            {**_submitted(), "asset_music_id": "", "media_url_music": ""},
            profile=profile,
        )
        assert overrides.get("asset_music_id") == ""
        assert overrides.get("media_url_music") == ""

    def test_auto_clears_bg_clip_and_outro_pairs(self):
        profile = _StubProfile(
            asset_bg_clip_id=_Setting("b-uuid", is_overridden=True),
            media_url_bg_clip=_Setting("http://b", is_overridden=True),
            asset_outro_clip_id=_Setting("o-uuid", is_overridden=True),
            media_url_outro=_Setting("http://o", is_overridden=True),
        )
        overrides = form_overrides(
            {
                **_submitted(),
                "asset_bg_clip_id": "",
                "media_url_bg_clip": "",
                "asset_outro_clip_id": "",
                "media_url_outro": "",
            },
            profile=profile,
        )
        assert overrides.get("asset_bg_clip_id") == ""
        assert overrides.get("media_url_bg_clip") == ""
        assert overrides.get("asset_outro_clip_id") == ""
        assert overrides.get("media_url_outro") == ""

    def test_auto_watermark_pair_cleared(self):
        profile = _StubProfile(
            asset_watermark_id=_Setting("w-uuid", is_overridden=True),
            media_url_watermark=_Setting("http://w", is_overridden=True),
        )
        overrides = form_overrides(
            {**_submitted(), "asset_watermark_id": "", "media_url_watermark": ""},
            profile=profile,
        )
        assert overrides.get("asset_watermark_id") == ""
        assert overrides.get("media_url_watermark") == ""

    def test_auto_font_has_no_url_pair(self):
        profile = _StubProfile(asset_font_id=_Setting("f-uuid", is_overridden=True))
        overrides = form_overrides({**_submitted(), "asset_font_id": ""}, profile=profile)
        assert overrides.get("asset_font_id") == ""
        assert not any(key.startswith("media_url_font") for key in overrides)

    def test_auto_without_override_creates_no_entry(self):
        profile = _StubProfile(asset_music_id="m-uuid")
        overrides = form_overrides({**_submitted(), "asset_music_id": ""}, profile=profile)
        assert "asset_music_id" not in overrides

    def test_auto_without_profile_creates_no_entry(self):
        overrides = form_overrides({**_submitted(), "asset_music_id": ""}, profile=None)
        assert "asset_music_id" not in overrides

    def test_unsubmitted_asset_selects_are_untouched(self):
        profile = _StubProfile(
            asset_music_id=_Setting("m-uuid", is_overridden=True),
            asset_font_id=_Setting("f-uuid", is_overridden=True),
            asset_bg_clip_id=_Setting("b-uuid", is_overridden=True),
            asset_outro_clip_id=_Setting("o-uuid", is_overridden=True),
            asset_watermark_id=_Setting("w-uuid", is_overridden=True),
        )
        overrides = form_overrides(_submitted(), profile=profile)
        for key in (
            "asset_music_id",
            "asset_font_id",
            "asset_bg_clip_id",
            "asset_outro_clip_id",
            "asset_watermark_id",
        ):
            assert key not in overrides

    def test_reselected_current_id_still_persists(self):
        profile = _StubProfile(asset_music_id=_Setting("m-uuid", is_overridden=True))
        overrides = form_overrides({**_submitted(), "asset_music_id": "m-uuid"}, profile=profile)
        assert overrides.get("asset_music_id") == "m-uuid"


class TestPhase2PanelNegativeHoldsPrefill:
    def test_negative_only_holds_prefill_hidden_input(self):
        import shorts_creator.ui.pages.new_project as np

        profile = _StubProfile(section_holds=_Setting({"message": -0.5}, is_overridden=True))
        markup = str(np._phase2_panel(profile))
        segment = markup.split('name="section_holds"')[1]
        assert 'value="{&quot;message&quot;: -0.5}"' in segment


def _knob_attr(markup: str, widget_id: str, attr: str):
    row = markup.split(f'id="{widget_id}"')[1].split(">")[0]
    match = re.search(attr + r'="([^"]*)"', row)
    return match.group(1) if match else None


class TestPacingKnobDataBuiltin:
    """Gap E1: the pacing knob reset must restore the built-in default (the
    value with the project's overrides suppressed), shipped as data_builtin
    next to the resolved data_default. With no override the two agree."""

    def test_overridden_message_pacing_knob_carries_builtin(self):
        import shorts_creator.ui.pages.new_project as np

        profile = _StubProfile(section_holds=_Setting({"message": 1.5}, is_overridden=True))
        builtin = _StubProfile(section_holds={})
        markup = str(np._phase2_panel(profile, builtin))
        assert _knob_attr(markup, "new-project-message-pacing", "data-default") == "2.5"
        assert _knob_attr(markup, "new-project-message-pacing", "data-builtin") == "1"

    def test_neutral_knob_builtin_equals_default(self):
        import shorts_creator.ui.pages.new_project as np

        markup = str(np._phase2_panel(_StubProfile(), _StubProfile()))
        for widget_id, value in (
            ("new-project-hold-hook", "0"),
            ("new-project-message-pacing", "1"),
            ("new-project-hold-conclusion", "0"),
        ):
            assert _knob_attr(markup, widget_id, "data-default") == value
            assert _knob_attr(markup, widget_id, "data-builtin") == value

    def test_override_equal_to_builtin_does_not_diverge(self):
        import shorts_creator.ui.pages.new_project as np

        profile = _StubProfile(section_holds=_Setting({"hook": 0.0}, is_overridden=True))
        markup = str(np._phase2_panel(profile, _StubProfile(section_holds={})))
        assert _knob_attr(markup, "new-project-hold-hook", "data-default") == "0"
        assert _knob_attr(markup, "new-project-hold-hook", "data-builtin") == "0"

    def test_overridden_hook_and_conclusion_knobs_carry_builtin(self):
        import shorts_creator.ui.pages.new_project as np

        profile = _StubProfile(
            section_holds=_Setting({"hook": 0.4, "conclusion": 0.3}, is_overridden=True)
        )
        markup = str(np._phase2_panel(profile, _StubProfile(section_holds={})))
        assert _knob_attr(markup, "new-project-hold-hook", "data-default") == "0.4"
        assert _knob_attr(markup, "new-project-hold-hook", "data-builtin") == "0"
        assert _knob_attr(markup, "new-project-hold-conclusion", "data-default") == "0.3"
        assert _knob_attr(markup, "new-project-hold-conclusion", "data-builtin") == "0"
