from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProfileSource,
    ProjectProfileOverrides,
    ResolvedSetting,
    validate_profile,
)


def test_override_model_uses_none_for_inherited_values():
    overrides = ProjectProfileOverrides()
    assert overrides.duration_seconds is None
    assert overrides.asset_music_id is None


def test_effective_profile_keeps_provenance_per_field():
    profile = EffectiveProjectProfile(
        duration_seconds=45,
        duration_source=ProfileSource.PROJECT,
        caption_style="highlight",
        caption_style_source=ProfileSource.FORMAT,
    )
    assert profile.duration_source is ProfileSource.PROJECT
    assert profile.caption_style_source is ProfileSource.FORMAT


def test_effective_profile_accepts_resolved_settings_directly():
    profile = EffectiveProjectProfile(
        duration_seconds=ResolvedSetting(45, ProfileSource.PROJECT, True),
        caption_style=ResolvedSetting("highlight", ProfileSource.FORMAT, False),
    )
    assert profile.duration_seconds.value == 45
    assert profile.duration_source is ProfileSource.PROJECT
    assert profile.caption_style_source is ProfileSource.FORMAT


def test_snapshot_dict_returns_json_safe_values_without_sources():
    profile = EffectiveProjectProfile(
        duration_seconds=ResolvedSetting(45, ProfileSource.PROJECT, True),
        caption_style=ResolvedSetting("highlight", ProfileSource.FORMAT, False),
    )
    snapshot = profile.snapshot_dict()
    assert snapshot["duration_seconds"] == 45
    assert snapshot["caption_style"] == "highlight"
    assert "duration_source" not in snapshot


def test_validation_rejects_non_positive_duration():
    errors = validate_profile({"duration_seconds": 0})
    assert errors["duration_seconds"] == "must be greater than zero"


def test_validation_rejects_unsupported_caption_style():
    errors = validate_profile({"caption_style": "fancy"})
    assert errors["caption_style"] == "unsupported caption style"
    assert validate_profile({"caption_style": "highlight"}) == {}
    assert validate_profile({"caption_style": "plain"}) == {}
    assert validate_profile({"caption_style": ""}) == {}


def test_validation_rejects_unsupported_format_name():
    errors = validate_profile({"format_name": "no-such-format"})
    assert errors["format_name"] == "unsupported format name"
    assert validate_profile({"format_name": "narrated"}) == {}


def test_validation_rejects_unsupported_stock_provider():
    errors = validate_profile({"stock_provider": "shutterstock"})
    assert errors["stock_provider"] == "unsupported stock provider"
    assert validate_profile({"stock_provider": "auto"}) == {}
    assert validate_profile({"stock_provider": "pexels"}) == {}
    assert validate_profile({"stock_provider": "pixabay"}) == {}
    assert validate_profile({"stock_provider": ""}) == {}


def test_validation_accepts_bg_mode_video_or_image():
    assert validate_profile({"bg_mode": "video"}) == {}
    assert validate_profile({"bg_mode": "image"}) == {}
    assert validate_profile({"bg_mode": ""}) == {}
    errors = validate_profile({"bg_mode": "slideshow"})
    assert errors["bg_mode"] == "unsupported background mode"


def test_validation_rejects_non_str_outro_text():
    errors = validate_profile({"outro_text": 123})
    assert errors["outro_text"] == "must be text"
    assert validate_profile({"outro_text": ""}) == {}
    assert validate_profile({"outro_text": "See you next time"}) == {}


def test_validation_rejects_bad_uppercase_knob():
    errors = validate_profile({"style": {"uppercase": "yes"}})
    assert errors["style"] == "uppercase must be a boolean"
    assert validate_profile({"style": {"uppercase": True}}) == {}
    assert validate_profile({"style": {"uppercase": False}}) == {}


def test_validation_rejects_out_of_range_scrim_alpha():
    errors = validate_profile({"style": {"scrim_alpha": 1.5}})
    assert errors["style"] == "scrim_alpha must be between 0 and 1"
    assert validate_profile({"style": {"scrim_alpha": 0.0}}) == {}
    assert validate_profile({"style": {"scrim_alpha": 1.0}}) == {}


def test_validation_rejects_bad_watermark_corner():
    errors = validate_profile({"layout": {"watermark_corner": "middle"}})
    assert (
        errors["layout"]
        == "watermark_corner must be one of bottom_right, bottom_left, top_right, top_left"
    )
    assert validate_profile({"layout": {"watermark_corner": "top_left"}}) == {}


def test_validation_rejects_out_of_range_watermark_knobs():
    errors = validate_profile(
        {
            "layout": {
                "watermark_size_pct": 99,
                "watermark_opacity": 2.0,
                "watermark_margin_px": -3,
            }
        }
    )
    assert errors["layout"] == (
        "watermark_size_pct must be between 5 and 30; "
        "watermark_opacity must be between 0.1 and 1; "
        "watermark_margin_px must be between 0 and 200"
    )
    assert (
        validate_profile(
            {
                "layout": {
                    "watermark_size_pct": 15,
                    "watermark_opacity": 0.5,
                    "watermark_margin_px": 20,
                }
            }
        )
        == {}
    )


def test_validation_rejects_out_of_range_music_and_fade_knobs():
    errors = validate_profile(
        {
            "layout": {
                "music_volume": 0.9,
                "music_fade_seconds": 0.1,
                "fade_out_seconds": 9.0,
            }
        }
    )
    assert errors["layout"] == (
        "music_volume must be between 0.05 and 0.5; "
        "music_fade_seconds must be between 0.5 and 6; "
        "fade_out_seconds must be between 0 and 3"
    )
    assert (
        validate_profile(
            {
                "layout": {
                    "music_volume": 0.3,
                    "music_fade_seconds": 4.0,
                    "fade_out_seconds": 2.0,
                }
            }
        )
        == {}
    )


def test_validation_rejects_bad_voice_preset():
    errors = validate_profile({"voice_preset": "whispery"})
    assert errors["voice_preset"] == "voice_preset must be one of natural, dramatic, energetic"
    assert validate_profile({"voice_preset": "dramatic"}) == {}


def test_validation_rejects_out_of_range_hook_lead_in():
    errors = validate_profile({"hook_lead_in_seconds": 9.0})
    assert errors["hook_lead_in_seconds"] == "hook_lead_in_seconds must be between 0 and 3"
    assert validate_profile({"hook_lead_in_seconds": 1.5}) == {}
    assert validate_profile({"hook_lead_in_seconds": 0.0}) == {}


def test_validation_rejects_bad_voice_list_fields():
    errors = validate_profile({"banned_topics": "politics"})
    assert errors["banned_topics"] == "must be a list of strings"
    errors = validate_profile({"tone_rules": [1, 2]})
    assert errors["tone_rules"] == "must be a list of strings"
    assert validate_profile({"banned_topics": ["politics"]}) == {}
    assert validate_profile({"tone_rules": ["no jargon"]}) == {}
    errors = validate_profile({"audience_persona": 42})
    assert errors["audience_persona"] == "must be text"
    assert validate_profile({"audience_persona": "busy founders"}) == {}


def test_validation_accepts_partial_and_empty_dicts():
    assert validate_profile({}) == {}
    assert validate_profile({"caption_style": "plain"}) == {}
    errors = validate_profile({"duration_seconds": 0})
    assert set(errors) == {"duration_seconds"}


def test_overrides_accept_composer_fields():
    ov = ProjectProfileOverrides(
        pacing_wps=2.7,
        hook_text="Custom hook here",
        sections=["message", "metaphor"],
        section_texts={"message": "My message"},
        style={"chunk_size": 2},
        palette={"highlight_colour": "0xFF0000AA"},
        layout={"anchor": "lower_third", "block_width_pct": 70},
        stages={"music": True, "watermark": False},
    )
    assert ov.pacing_wps == 2.7
    assert ov.sections == ["message", "metaphor"]
    assert ov.stages == {"music": True, "watermark": False}


def test_validate_profile_composer_rules():
    errors = validate_profile(
        {
            "pacing_wps": "abc",
            "layout": {"anchor": "upper_third"},
            "palette": {"highlight_colour": "red"},
            "stages": {"music": "yes"},
        }
    )
    assert "pacing_wps" in errors
    assert "layout" in errors
    assert "palette" in errors
    assert "stages" in errors

    errors = validate_profile(
        {
            "pacing_wps": 2.6,
            "layout": {"anchor": "center"},
            "palette": {"highlight_colour": "0xFF0000AA"},
            "stages": {"music": True, "outro": True},
        }
    )
    assert errors == {}
