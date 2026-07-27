from shorts_creator.controllers.api.composer_presets_bundles import STARTER_PRESETS
from shorts_creator.pipeline.compose import (
    _line_text,
    build_compose_plan,
    chunk_word_frames,
    hook_font_size,
)
from shorts_creator.pipeline.pipeline import FADE_IN_SECONDS, FADE_OUT_SECONDS
from shorts_creator.pipeline.render_config import RenderConfig
from shorts_creator.pipeline.script_parser import ParsedScript

_SCRIPT = ParsedScript(
    title="Test",
    duration_seconds=5.0,
    word_count=10,
    pacing_wps=2.0,
    hook="Hook",
    hook_seconds=3.0,
    message_lines=["Message one", "Message two"],
    message_seconds=4.0,
    metaphor="Metaphor",
    metaphor_seconds=2.0,
    conclusion="Conclusion",
    conclusion_seconds=2.0,
    emotional_arc=[],
    parallel_structure="",
    hook_score="",
)


def _words(timings: list[tuple[str, float]]) -> list[dict]:
    return [{"word": w, "start": s, "end": e} for w, s, e in timings]


def test_plan_timing_math_with_outro():
    line_data = [
        ("line_0.wav", 3.0, _words([("A", 0.0, 3.0)])),
        ("line_1.wav", 2.0, _words([("B", 0.0, 2.0)])),
    ]
    plan = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
    )

    assert plan.total_frames == 90 + 60 + 90
    assert plan.narration_end_frames == 90 + 60
    assert plan.fade_in == FADE_IN_SECONDS
    assert plan.fade_out == FADE_OUT_SECONDS
    assert plan.encode.codec == "hevc_nvenc"
    assert plan.encode.bitrate == "10M"
    assert plan.encode.resolution == "1080x1920"
    assert plan.encode.fps == 30


def test_plan_respects_music_and_fade_knobs():
    line_data = [
        ("line_0.wav", 3.0, _words([("A", 0.0, 3.0)])),
        ("line_1.wav", 2.0, _words([("B", 0.0, 2.0)])),
    ]
    cfg = RenderConfig(music_volume=0.35, fade_out_seconds=2.5)
    plan = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
        music_bed_path="/tmp/music.wav",
        render_config=cfg,
    )
    music_layers = [a for a in plan.audio_layers if a.volume == 0.35]
    assert len(music_layers) == 1
    assert plan.fade_out == 2.5


def test_line_pool_orders_hook_then_top_items_then_message():
    script = ParsedScript(
        title="T",
        duration_seconds=40.0,
        word_count=100,
        pacing_wps=2.5,
        hook="Hook",
        hook_seconds=3.0,
        message_lines=["Message"],
        message_seconds=10.0,
        metaphor="Metaphor",
        metaphor_seconds=2.0,
        conclusion="Conclusion",
        conclusion_seconds=4.0,
        emotional_arc=[],
        parallel_structure="",
        hook_score="",
        top_items=["1. One", "2. Two", "3. Three", "4. Four", "5. Five"],
        top_items_seconds=21.0,
    )
    lines = [_line_text(script, i) for i in range(9)]
    assert lines == [
        "Hook",
        "1. One",
        "2. Two",
        "3. Three",
        "4. Four",
        "5. Five",
        "Message",
        "Metaphor",
        "Conclusion",
    ]


def test_styleless_plan_has_no_hook_or_caption_overlays():
    line_data = [
        ("line_0.wav", 3.0, _words([("A", 0.0, 3.0)])),
        ("line_1.wav", 2.0, _words([("B", 0.0, 2.0)])),
    ]
    plan = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        caption_styles=[],
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
    )
    text_overlays = [
        o for o in plan.overlays if "hook.mov" in o.asset.uri or "caption_" in o.asset.uri
    ]
    assert text_overlays == []
    assert len(plan.overlays) == 2  # background + outro only

    with_styles = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
    )
    assert any("hook.mov" in o.asset.uri for o in with_styles.overlays)


def test_styleless_plan_with_top_items_keeps_hook_and_ranked_screens():
    script = ParsedScript(
        title="T",
        duration_seconds=30.0,
        word_count=60,
        pacing_wps=2.0,
        hook="Hook",
        hook_seconds=3.0,
        message_lines=[],
        message_seconds=0.0,
        metaphor="",
        metaphor_seconds=0.0,
        conclusion="Conclusion",
        conclusion_seconds=2.0,
        emotional_arc=[],
        parallel_structure="",
        hook_score="",
        top_items=["1. One", "2. Two", "3. Three"],
        top_items_seconds=9.0,
    )
    line_data = [
        ("line_0.wav", 3.0, _words([("A", 0.0, 3.0)])),
        ("line_1.wav", 3.0, _words([("B", 0.0, 3.0)])),
        ("line_2.wav", 3.0, _words([("C", 0.0, 3.0)])),
        ("line_3.wav", 3.0, _words([("D", 0.0, 3.0)])),
        ("line_4.wav", 2.0, _words([("E", 0.0, 2.0)])),
    ]
    plan = build_compose_plan(
        script,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        temp_dir="/tmp/td",
        caption_styles=[],
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
    )

    uris = [o.asset.uri for o in plan.overlays]
    assert any(u.endswith("hook.mov") for u in uris)
    assert all(any(u.endswith(f"rank_{i}.mov") for u in uris) for i in range(1, 4))
    assert not any("caption_" in u for u in uris)

    hook = next(o for o in plan.overlays if o.asset.uri.endswith("hook.mov"))
    assert (hook.start, hook.end) == (0.0, 3.0)
    for i in range(1, 4):
        layer = next(o for o in plan.overlays if o.asset.uri.endswith(f"rank_{i}.mov"))
        assert layer.start == i * 3.0
        assert layer.end == (i + 1) * 3.0


def test_styleless_plan_with_top_items_and_list_style_uses_one_full_list_screen():
    script = ParsedScript(
        title="T",
        duration_seconds=30.0,
        word_count=60,
        pacing_wps=2.0,
        hook="Hook",
        hook_seconds=3.0,
        message_lines=[],
        message_seconds=0.0,
        metaphor="",
        metaphor_seconds=0.0,
        conclusion="Conclusion",
        conclusion_seconds=2.0,
        emotional_arc=[],
        parallel_structure="",
        hook_score="",
        top_items=["1. One", "2. Two", "3. Three"],
        top_items_seconds=9.0,
    )
    line_data = [
        ("line_0.wav", 3.0, _words([("A", 0.0, 3.0)])),
        ("line_1.wav", 3.0, _words([("B", 0.0, 3.0)])),
        ("line_2.wav", 3.0, _words([("C", 0.0, 3.0)])),
        ("line_3.wav", 3.0, _words([("D", 0.0, 3.0)])),
        ("line_4.wav", 2.0, _words([("E", 0.0, 2.0)])),
    ]
    plan = build_compose_plan(
        script,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        temp_dir="/tmp/td",
        caption_styles=[],
        caption_style="list",
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
    )

    uris = [o.asset.uri for o in plan.overlays]
    assert any(u.endswith("hook.mov") for u in uris)
    assert not any(u.endswith(f"rank_{i}.mov") for u in uris for i in range(1, 4))
    assert not any("caption_" in u for u in uris)

    hook = next(o for o in plan.overlays if o.asset.uri.endswith("hook.mov"))
    assert (hook.start, hook.end) == (0.0, 3.0)
    list_layer = next(o for o in plan.overlays if o.asset.uri.endswith("list.mov"))
    assert (list_layer.start, list_layer.end) == (3.0, 12.0)


def test_compose_default_caption_style_is_highlight_and_unknowns_fall_back():
    line_data = [
        ("line_0.wav", 3.0, _words([("A", 0.0, 3.0)])),
        ("line_1.wav", 2.0, _words([("B", 0.0, 2.0)])),
    ]
    default_plan = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        temp_dir="/tmp/td",
        caption_styles=["highlight"],
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
    )
    uris = [o.asset.uri for o in default_plan.overlays]
    assert any("caption_" in u for u in uris)

    stray_plan = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        temp_dir="/tmp/td",
        caption_styles=["highlight"],
        caption_style="number",
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
    )
    stray_uris = [o.asset.uri for o in stray_plan.overlays]
    assert any("caption_" in u for u in stray_uris)
    assert [o.asset.uri for o in stray_plan.overlays] == uris


def test_reel_pipeline_caption_styles_defaults_and_empty():
    from shorts_creator.pipeline.pipeline import ReelPipeline

    try:
        default = ReelPipeline()
        assert default.caption_styles == ["highlight"]
        bare = ReelPipeline(caption_styles=[])
        assert bare.caption_styles == []
    finally:
        default.cleanup()
        bare.cleanup()


def test_plan_layer_order_and_windows():
    words = _words(
        [
            ("one", 0.0, 0.5),
            ("two", 0.5, 1.0),
            ("three", 1.0, 1.4),
            ("four", 1.4, 1.8),
            ("five", 1.8, 2.0),
        ]
    )
    line_data = [
        ("line_0.wav", 3.0, _words([("A", 0.0, 3.0)])),
        ("line_1.wav", 2.0, words),
    ]
    plan = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
    )

    footage, hook, *captions, outro = plan.overlays
    assert footage.start == 0.0
    assert footage.end == plan.narration_end_frames / 30.0
    assert footage.fade_out == 0.0

    assert hook.start == 0.0
    assert hook.end == 90 / 30.0

    assert len(captions) == 2
    first, second = captions
    assert first.start == 90 / 30.0
    assert first.end == (90 + 42) / 30.0
    assert first.fade_out == 0.0
    assert second.start == (90 + 42) / 30.0
    assert second.end == (90 + 60) / 30.0
    assert second.fade_out == 0.0

    assert outro.start == plan.narration_end_frames / 30.0
    assert outro.end == plan.total_frames / 30.0
    assert outro.fade_out == 0.0


def test_plan_audio_layers_at_cumulative_offsets():
    line_data = [
        ("line_0.wav", 3.0, _words([("A", 0.0, 3.0)])),
        ("line_1.wav", 2.0, _words([("B", 0.0, 2.0)])),
    ]
    plan = build_compose_plan(_SCRIPT, line_data, bg_path="/tmp/bg.mp4", fps=30.0)

    assert len(plan.audio_layers) == 2
    assert plan.audio_layers[0].start == 0.0
    assert plan.audio_layers[1].start == 90 / 30.0
    assert all(layer.volume == 1.0 for layer in plan.audio_layers)


def test_holds_extend_line_windows():
    line_data = [
        ("line_0.wav", 2.0, _words([("A", 0.0, 2.0)])),
        ("line_1.wav", 2.0, _words([("B", 0.0, 2.0)])),
    ]
    script = ParsedScript(
        title="T",
        duration_seconds=10.0,
        word_count=20,
        pacing_wps=2.0,
        hook="Hook",
        hook_seconds=2.0,
        message_lines=["Message"],
        message_seconds=2.0,
        metaphor="",
        metaphor_seconds=0.0,
        conclusion="",
        conclusion_seconds=0.0,
        emotional_arc=[],
        parallel_structure="",
        hook_score="",
        section_names=["hook", "message"],
    )
    cfg = RenderConfig(section_holds={"hook": 0.5, "conclusion": 0.25})
    plan = build_compose_plan(
        script,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
        render_config=cfg,
    )

    hook = next(o for o in plan.overlays if o.asset.uri.endswith("hook.mov"))
    assert (hook.start, hook.end) == (0.0, 75 / 30.0)
    assert plan.narration_end_frames == 75 + 60
    assert plan.audio_layers[1].start == 75 / 30.0
    assert plan.total_frames == 75 + 60 + 90


def test_fast_cuts_preset_negative_hold_shortens_message_window():
    """The 'Fast cuts' starter ships section_holds {"message": -0.5}
    (composer_presets_bundles.py:12): resolution keeps it and the compose
    plan's message window shortens vs the default (R6)."""
    fast_cuts = next(p for p in STARTER_PRESETS if p["name"] == "Fast cuts")
    cfg = RenderConfig.resolve(None, fast_cuts["payload"])
    assert cfg.section_holds == {"message": -0.5}

    line_data = [
        ("line_0.wav", 2.0, _words([("A", 0.0, 2.0)])),
        ("line_1.wav", 2.0, _words([("B", 0.0, 2.0)])),
    ]
    script = ParsedScript(
        title="T",
        duration_seconds=10.0,
        word_count=20,
        pacing_wps=2.0,
        hook="Hook",
        hook_seconds=2.0,
        message_lines=["Message"],
        message_seconds=2.0,
        metaphor="",
        metaphor_seconds=0.0,
        conclusion="",
        conclusion_seconds=0.0,
        emotional_arc=[],
        parallel_structure="",
        hook_score="",
        section_names=["hook", "message"],
    )
    fast = build_compose_plan(
        script,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
        render_config=cfg,
    )
    plain = build_compose_plan(
        script,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
    )
    assert fast.narration_end_frames < plain.narration_end_frames
    assert fast.narration_end_frames == 60 + 45
    assert fast.total_frames == 60 + 45 + 90


def test_plan_music_bed_layer():
    line_data = [("line_0.wav", 3.0, _words([("A", 0.0, 3.0)]))]
    plan = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        temp_dir="/tmp/td",
        music_bed_path="/tmp/music.mp3",
    )

    assert len(plan.audio_layers) == 2
    assert plan.audio_layers[1].volume == 0.2
    assert plan.audio_layers[1].asset.uri == "file:///tmp/td/music_bed.wav"


def test_plan_watermark_layer():
    line_data = [("line_0.wav", 3.0, _words([("A", 0.0, 3.0)]))]
    plan = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        temp_dir="/tmp/td",
        watermark_path="/tmp/wm.png",
    )

    watermark = plan.overlays[-1]
    assert watermark.start == 0.0
    assert watermark.end == plan.total_frames / 30.0


def test_plan_black_base_asset():
    line_data = [("line_0.wav", 3.0, _words([("A", 0.0, 3.0)]))]
    plan = build_compose_plan(_SCRIPT, line_data, bg_path="/tmp/bg.mp4", fps=30.0)

    assert plan.base_asset.mime_type == "video/mp4"
    assert plan.base_asset.provider == "local-http"
    assert plan.base_asset.uri is not None
    assert plan.base_asset.uri.startswith("file://")
    assert plan.base_asset.uri.endswith("black_base.mp4")


def test_plan_no_words_fallback():
    line_data = [
        ("line_0.wav", 3.0, _words([("A", 0.0, 3.0)])),
        ("line_1.wav", 2.0, []),
    ]
    plan = build_compose_plan(_SCRIPT, line_data, bg_path="/tmp/bg.mp4", fps=30.0)

    captions = plan.overlays[2:]
    assert len(captions) == 1
    assert captions[0].start == 90 / 30.0
    assert captions[0].end == (90 + 60) / 30.0
    assert captions[0].fade_out == 0.0


def test_chunk_word_frames_hand_off_at_next_word_start():
    chunk = _words([("Progress", 0.0, 0.27), ("beats", 0.37, 0.57), ("perfection", 0.63, 0.93)])
    frames = chunk_word_frames(chunk, seg_start_rel=0, seg_end_rel=52, fps=30.0, per_line_frames=52)

    assert frames[0] == 11
    assert frames[1] == 8
    assert frames[2] == 9


def test_chunk_word_frames_last_word_holds_only_its_spoken_end():
    chunk = _words([("Focus", 1.8, 2.1), ("one", 2.13, 2.4), ("thing", 2.43, 2.7)])
    frames = chunk_word_frames(
        chunk, seg_start_rel=54, seg_end_rel=90, fps=30.0, per_line_frames=90
    )

    assert frames == [10, 9, 8]


def test_chunk_word_frames_last_word_clamped_to_segment_end():
    chunk = _words([("Go", 0.0, 10.0)])
    frames = chunk_word_frames(chunk, seg_start_rel=0, seg_end_rel=52, fps=30.0, per_line_frames=60)

    assert frames == [52]


def test_plan_chunk_size_follows_render_config():
    from shorts_creator.pipeline.render_config import RenderConfig

    words = _words(
        [
            ("w1", 0.0, 0.4),
            ("w2", 0.4, 0.8),
            ("w3", 0.8, 1.2),
            ("w4", 1.2, 1.6),
            ("w5", 1.6, 2.0),
            ("w6", 2.0, 2.4),
        ]
    )
    line_data = [
        ("line_0.wav", 3.0, _words([("A", 0.0, 3.0)])),
        ("line_1.wav", 2.4, words),
    ]
    plan = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        caption_groups_by_idx={1: [words]},
        render_config=RenderConfig(caption_max_words=2),
    )
    captions = [o for o in plan.overlays if "caption_" in o.asset.uri]
    assert len(captions) == 3

    default = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        caption_groups_by_idx={1: [words]},
    )
    assert len([o for o in default.overlays if "caption_" in o.asset.uri]) == 2


def test_hook_font_size_follows_block_width_declaration():
    from shorts_creator.pipeline.render_config import RenderConfig

    texts = ["Wake up", "and grind"]
    wide = hook_font_size(texts, width=1080, height=1920)
    narrow = hook_font_size(
        texts,
        width=1080,
        height=1920,
        render_config=RenderConfig(hook_block_width_pct=40),
    )
    assert 0 < narrow < wide


def test_plan_bg_segments_create_adjacent_layers():
    line_data = [
        ("line_0.wav", 3.0, _words([("A", 0.0, 3.0)])),
        ("line_1.wav", 2.0, _words([("B", 0.0, 2.0)])),
        ("line_2.wav", 1.0, _words([("C", 0.0, 1.0)])),
    ]
    segments = [
        ("/tmp/seg0.mp4", 0, 90),
        ("/tmp/seg1.mp4", 90, 150),
        ("/tmp/seg2.mp4", 150, 180),
    ]
    plan = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        bg_segments=segments,
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
    )
    bg_layers = [o for o in plan.overlays if "seg" in o.asset.uri]
    assert len(bg_layers) == 3
    assert [(l.start, l.end) for l in bg_layers] == [
        (0.0, 3.0),
        (3.0, 5.0),
        (5.0, 6.0),
    ]
    assert bg_layers[-1].end == plan.narration_end_frames / 30.0
    assert not any(o.asset.uri.endswith("bg.mp4") for o in plan.overlays)


def test_steps_uses_rank_screens_with_checks_marker():
    # steps is style-less (no caption styles) -> compose emits a rank screen
    # per top item. Drive the real path: load the format, resolve its render
    # config, and build the plan with the format's actual declarations.
    from shorts_creator.contracts.pipeline import PIPELINE_CAPABILITIES
    from shorts_creator.formats import registry

    fmt = registry.get("steps")
    assert fmt is not None
    assert fmt.caption_styles == []
    assert "music_beat" in fmt.to_contract_side().requires_pipeline
    assert "music_beat" in PIPELINE_CAPABILITIES

    script = ParsedScript(
        title="T",
        duration_seconds=11.0,
        word_count=25,
        pacing_wps=2.0,
        hook="Hook",
        hook_seconds=3.0,
        message_lines=[],
        message_seconds=0.0,
        metaphor="",
        metaphor_seconds=0.0,
        conclusion="Conclusion",
        conclusion_seconds=2.0,
        emotional_arc=[],
        parallel_structure="",
        hook_score="",
        top_items=["One", "Two"],
        top_items_seconds=6.0,
    )
    line_data = [
        ("line_0.wav", 3.0, _words([("A", 0.0, 3.0)])),
        ("line_1.wav", 3.0, _words([("B", 0.0, 3.0)])),
        ("line_2.wav", 3.0, _words([("C", 0.0, 3.0)])),
    ]
    cfg = RenderConfig.resolve(fmt, {})
    assert cfg.ranked_number_scale == 1.4  # steps defaults: reach the render config
    plan = build_compose_plan(
        script,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        temp_dir="/tmp/td",
        caption_styles=list(fmt.caption_styles),
        render_config=cfg,
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
    )

    uris = [o.asset.uri for o in plan.overlays]
    assert any(u.endswith("hook.mov") for u in uris)
    assert all(any(u.endswith(f"rank_{i}.mov") for u in uris) for i in range(1, 3))
    assert not any("caption_" in u for u in uris)
    rank1 = next(o for o in plan.overlays if o.asset.uri.endswith("rank_1.mov"))
    assert (rank1.start, rank1.end) == (3.0, 6.0)


def test_reel_pipeline_rank_style_defaults_and_selection():
    from shorts_creator.pipeline.pipeline import ReelPipeline

    default = None
    checked = None
    try:
        default = ReelPipeline()
        assert default.rank_style == "number"
        checked = ReelPipeline(rank_style="check")
        assert checked.rank_style == "check"
    finally:
        if default:
            default.cleanup()
        if checked:
            checked.cleanup()


def test_rank_style_selects_checked_renderer():
    from shorts_creator.pipeline.pipeline import (
        _rank_render_clip,
        _render_checked_clip,
        _render_ranked_clip,
    )

    assert _rank_render_clip("check") is _render_checked_clip
    assert _rank_render_clip("number") is _render_ranked_clip


def test_plan_bg_segments_none_keeps_single_window():
    line_data = [
        ("line_0.wav", 3.0, _words([("A", 0.0, 3.0)])),
        ("line_1.wav", 2.0, _words([("B", 0.0, 2.0)])),
    ]
    plan = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
    )
    bg_layers = [o for o in plan.overlays if o.asset.uri.endswith("bg.mp4")]
    assert len(bg_layers) == 1
    assert (bg_layers[0].start, bg_layers[0].end) == (0.0, 150 / 30.0)


def test_stages_background_off_drops_bg_layer_keeps_text_overlays():
    line_data = [
        ("line_0.wav", 3.0, _words([("A", 0.0, 3.0)])),
        ("line_1.wav", 2.0, _words([("B", 0.0, 2.0)])),
    ]
    off = {"background": False, "music": False, "outro": False, "watermark": False}
    plan = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
        watermark_path="/tmp/wm.png",
        stages=off,
    )
    uris = [o.asset.uri for o in plan.overlays]
    assert not any(u.endswith("bg.mp4") for u in uris)
    assert not any("watermark" in u for u in uris)
    assert any("hook.mov" in u for u in uris)
    assert sum("caption_" in u for u in uris) >= 1
    assert any(u.endswith("outro.mp4") for u in uris)


def test_stages_defaults_keep_background_and_watermark():
    line_data = [("line_0.wav", 3.0, _words([("A", 0.0, 3.0)]))]
    plan = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
        watermark_path="/tmp/wm.png",
    )
    uris = [o.asset.uri for o in plan.overlays]
    assert any(u.endswith("bg.mp4") for u in uris)
    assert any("watermark" in u for u in uris)


def test_background_motion_defaults_off():
    from shorts_creator.pipeline.render_config import RenderConfig

    assert RenderConfig().background_motion == "none"


def test_plan_carries_outro_text_overlay_when_given():
    from lexigram.contracts.multimedia.types import ComposeLayer

    line_data = [
        ("line_0.wav", 3.0, _words([("A", 0.0, 3.0)])),
        ("line_1.wav", 2.0, _words([("B", 0.0, 2.0)])),
    ]
    plan = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
        outro_text_path="/tmp/outro_text.mov",
    )

    text_layers = [
        layer
        for layer in plan.overlays
        if isinstance(layer, ComposeLayer) and layer.asset.uri.endswith("outro_text.mov")
    ]
    assert len(text_layers) == 1
    outro_layer = next(
        layer
        for layer in plan.overlays
        if isinstance(layer, ComposeLayer) and layer.asset.uri.endswith("outro.mp4")
    )
    assert text_layers[0].start == outro_layer.start
    assert text_layers[0].end == outro_layer.end


def test_plan_has_no_text_overlay_without_path():
    line_data = [("line_0.wav", 3.0, _words([("A", 0.0, 3.0)]))]
    plan = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
    )
    assert not any(layer.asset.uri.endswith("outro_text.mov") for layer in plan.overlays)
