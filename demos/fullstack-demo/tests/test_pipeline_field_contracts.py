"""Locked contracts for composer fields that intentionally do NOT drive the
render pipeline directly (see 2026-08-16-pipeline-field-parity plan)."""

from shorts_creator.pipeline.compose import build_compose_plan
from shorts_creator.pipeline.pipeline import ReelPipeline, held_line_frames
from shorts_creator.pipeline.script_parser import ParsedScript

_SCRIPT = ParsedScript(
    title="Contract",
    duration_seconds=5.0,
    word_count=10,
    pacing_wps=2.0,
    hook="Hook",
    hook_seconds=3.0,
    message_lines=["Message one"],
    message_seconds=2.0,
    metaphor="Metaphor",
    metaphor_seconds=2.0,
    conclusion="Conclusion",
    conclusion_seconds=2.0,
    emotional_arc=[],
    parallel_structure="",
    hook_score="",
)


def _words(timings):
    return [{"word": w, "start": s, "end": e} for w, s, e in timings]


def test_duration_seconds_does_not_stretch_the_render_length():
    """Contract: duration_seconds is a desired-length hint. The composer
    plan's length is derived from narration TTS + outro, not the hint."""
    line_data = [("line_0.wav", 4.0, _words([("A", 0.0, 4.0)]))]
    plan_30 = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
    )
    plan_60 = build_compose_plan(
        _SCRIPT,
        line_data,
        bg_path="/tmp/bg.mp4",
        fps=30.0,
        outro_path="/tmp/outro.mp4",
        outro_seconds=3.0,
    )
    assert plan_30.total_frames == plan_60.total_frames == 30 * 4 + round(3.0 * 30)


def test_outro_text_reaches_pipeline_constructor():
    """Contract: outro_text is threaded into ReelPipeline from the snapshot
    (render_api.py:476); the pipeline stores it for the outro stage."""
    pipeline = ReelPipeline(output="/tmp/contract.mp4", outro_text="Bye!")
    assert pipeline.outro_text == "Bye!"


def test_pacing_and_sections_are_script_level_fields():
    """Contract: pacing_wps and sections belong to the script layer
    (scripts_api.py:122, script_service.py:50); they are never consumed by
    the render compose plan."""
    from shorts_creator.pipeline import compose as compose_mod

    src = ""
    if hasattr(compose_mod, "__file__"):
        with open(compose_mod.__file__) as fh:
            src = fh.read()
    assert "pacing_wps" not in src
    assert "sections" not in src


def test_negative_hold_shortens_window():
    """Contract (R6): negative section_holds SHORTEN the on-screen window
    below the TTS duration (audio continues unaffected)."""
    line_data = [("line_0.wav", 2.3, _words([("A", 0.0, 2.3)]))]
    base = held_line_frames(line_data, 30.0, {}, ["message"])[0]
    shortened = held_line_frames(line_data, 30.0, {"message": -0.5}, ["message"])[0]
    assert base == 69
    assert shortened == 54
    assert shortened < base


def test_extreme_negative_hold_floors_at_one_frame():
    """Contract (R6): the effective per-line window never drops below
    1 frame (a zero-length caption clip breaks ffmpeg composition)."""
    line_data = [("line_0.wav", 1.0, _words([("A", 0.0, 1.0)]))]
    frames = held_line_frames(line_data, 30.0, {"message": -50}, ["message"])
    assert frames == [1]


def test_negative_hold_short_line_floors_at_one_frame():
    """Contract (R6): a 0.2s line with hold -0.5 floors at 1 frame, not 0."""
    line_data = [("line_0.wav", 0.2, _words([("A", 0.0, 0.2)]))]
    frames = held_line_frames(line_data, 30.0, {"message": -0.5}, ["message"])
    assert frames == [1]
