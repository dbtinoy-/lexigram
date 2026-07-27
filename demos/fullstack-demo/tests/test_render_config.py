"""RenderConfig: default values equal the module constants they replace."""

from shorts_creator.pipeline.render_config import (
    RenderConfig,
    colour_is_hex,
)


def test_defaults_match_module_constants():
    cfg = RenderConfig()
    assert cfg.caption_font_size == 56
    assert cfg.caption_max_words == 3
    assert cfg.caption_highlight_colour == "0x7C5CFAFF"
    assert cfg.caption_outline_width == 2
    assert cfg.hook_min_font_size == 40
    assert cfg.hook_max_font_size == 110
    assert cfg.hook_char_width_factor == 0.55
    assert cfg.hook_line_height_factor == 1.3
    assert cfg.hook_block_width_pct == 80
    assert cfg.hook_block_height_pct == 70
    assert cfg.hook_line_gap_px == 18
    assert cfg.hook_line_target_size == 1
    assert cfg.ranked_number_scale == 1.6
    assert cfg.anchor == "center"
    assert cfg.pill_bg_colour == "0x000000C0"
    assert cfg.watermark_size_pct == 10.0
    assert cfg.watermark_opacity == 0.85
    assert cfg.watermark_margin_px == 48
    assert cfg.watermark_corner == "bottom_right"
    assert cfg.music_volume == 0.2
    assert cfg.music_fade_seconds == 2.0
    assert cfg.fade_out_seconds == 1.0
    assert cfg.caption_uppercase is False
    assert cfg.caption_scrim_alpha == 0.0


def test_anchor_enum_constrained():
    try:
        RenderConfig(anchor="upper_third")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unknown anchor")


def test_colour_validation():
    assert colour_is_hex("0x7C5CFAFF")
    assert not colour_is_hex("red")
    assert not colour_is_hex("0x7C5CFA")


def test_resolve_applies_composer_overrides():
    cfg = RenderConfig.resolve(
        None,
        {
            "style": {
                "chunk_size": 5,
                "caption_font_size": 68,
                "caption_outline_width": 4,
            },
            "palette": {
                "highlight_colour": "0xFF0000FF",
                "pill_bg_colour": "0xFFFFFF00",
            },
        },
    )
    assert cfg.caption_max_words == 5
    assert cfg.caption_font_size == 68
    assert cfg.caption_outline_width == 4
    assert cfg.caption_highlight_colour == "0xFF0000FF"
    assert cfg.pill_bg_colour == "0xFFFFFF00"


def test_resolve_ignores_unknown_style_keys():
    cfg = RenderConfig.resolve(None, {"style": {"bogus": 1}})
    assert cfg == RenderConfig()


def test_resolve_applies_new_knobs():
    cfg = RenderConfig.resolve(
        None,
        {
            "layout": {
                "watermark_size_pct": 15,
                "watermark_opacity": 0.5,
                "watermark_margin_px": 20,
                "watermark_corner": "top_left",
                "music_volume": 0.3,
                "music_fade_seconds": 4.0,
                "fade_out_seconds": 2.5,
            },
            "style": {"uppercase": True, "scrim_alpha": 0.4},
        },
    )
    assert cfg.watermark_size_pct == 15
    assert cfg.watermark_opacity == 0.5
    assert cfg.watermark_margin_px == 20
    assert cfg.watermark_corner == "top_left"
    assert cfg.music_volume == 0.3
    assert cfg.music_fade_seconds == 4.0
    assert cfg.fade_out_seconds == 2.5
    assert cfg.caption_uppercase is True
    assert cfg.caption_scrim_alpha == 0.4


def test_resolve_clamps_new_knobs():
    cfg = RenderConfig.resolve(
        None,
        {
            "layout": {
                "watermark_size_pct": 99,
                "watermark_opacity": 0.01,
                "watermark_margin_px": -5,
                "music_volume": 9.0,
                "music_fade_seconds": 0.1,
                "fade_out_seconds": 9.0,
            },
            "style": {"scrim_alpha": 7.0},
        },
    )
    assert cfg.watermark_size_pct == 30
    assert cfg.watermark_opacity == 0.1
    assert cfg.watermark_margin_px == 0
    assert cfg.music_volume == 0.5
    assert cfg.music_fade_seconds == 0.5
    assert cfg.fade_out_seconds == 3.0
    assert cfg.caption_scrim_alpha == 1.0


def test_resolve_ignores_garbage_new_knobs():
    cfg = RenderConfig.resolve(
        None,
        {
            "layout": {
                "watermark_size_pct": "big",
                "watermark_corner": "middle",
                "music_volume": "loud",
            },
            "style": {"uppercase": "yes", "scrim_alpha": None},
        },
    )
    assert cfg == RenderConfig()


def test_resolve_forwards_phase2_knobs():
    cfg = RenderConfig.resolve(
        None,
        {
            "style": {
                "background_motion": "zoom",
                "emphasis_style": "accent",
                "loudness_target_lufs": -16,
                "audio_normalize": True,
                "section_holds": {"hook": 0.5, "conclusion": 0.25},
                "stage_accents": {"hook": "warm"},
            },
        },
    )
    assert cfg.background_motion == "zoom"
    assert cfg.emphasis_style == "accent"
    assert cfg.loudness_target_lufs == -16
    assert cfg.audio_normalize is True
    assert cfg.section_holds == {"hook": 0.5, "conclusion": 0.25}
    assert cfg.stage_accents == {"hook": "warm"}


def test_resolve_forwards_phase2_knobs_top_level():
    cfg = RenderConfig.resolve(
        None,
        {
            "background_motion": "pan",
            "emphasis_style": "scale",
            "loudness_target_lufs": -12,
            "audio_normalize": False,
            "section_holds": {"metaphor": 1.0},
        },
    )
    assert cfg.background_motion == "pan"
    assert cfg.emphasis_style == "scale"
    assert cfg.loudness_target_lufs == -12
    assert cfg.audio_normalize is False
    assert cfg.section_holds == {"metaphor": 1.0}


def test_resolve_keeps_negative_section_holds():
    """Contract (R6): negative hold seconds are carried through resolution;
    positive = lengthen, negative = shorten the on-screen window."""
    cfg = RenderConfig.resolve(
        None,
        {"style": {"section_holds": {"message": -0.5}}},
    )
    assert cfg.section_holds == {"message": -0.5}


def test_resolve_drops_non_numeric_section_holds():
    """Contract (R6): non-number values (strings, bools) are still dropped."""
    cfg = RenderConfig.resolve(
        None,
        {"style": {"section_holds": {"message": "fast", "ok": True}}},
    )
    assert cfg.section_holds == {}


def test_resolve_ignores_garbage_phase2_knobs():
    cfg = RenderConfig.resolve(
        None,
        {
            "style": {
                "background_motion": "spiral",
                "emphasis_style": "confetti",
                "loudness_target_lufs": "loud",
                "audio_normalize": "yes",
                "section_holds": {"conclusion": "long", "ok": True},
            },
        },
    )
    assert cfg == RenderConfig()


def test_watermark_corner_enum_constrained():
    try:
        RenderConfig(watermark_corner="middle")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unknown watermark corner")
