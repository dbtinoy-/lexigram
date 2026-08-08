from shorts_creator.formats import registry as format_registry
from shorts_creator.pipeline.pipeline import _render_caption_frame
from shorts_creator.pipeline.render_config import RenderConfig
from shorts_creator.pipeline.script_parser import parse_script, to_pipeline_script

MYTH_SAVED = {
    "title": "M",
    "total_duration": 40,
    "sections": [
        {"name": "hook", "text": "H", "duration_seconds": 3},
        {"name": "claim", "text": "C", "duration_seconds": 4},
        {"name": "fact", "text": "F1", "duration_seconds": 7},
        {"name": "fact", "text": "F2", "duration_seconds": 7},
        {"name": "fact", "text": "F3", "duration_seconds": 7},
        {"name": "twist", "text": "T", "duration_seconds": 5},
        {"name": "conclusion", "text": "O", "duration_seconds": 5},
    ],
}


def test_myth_sections_fold_into_message_with_claim_and_twist():
    s = to_pipeline_script(MYTH_SAVED)
    assert s.fact_count == 3
    assert s.message_lines == ["C", "F1", "F2", "F3", "T"]
    assert s.claim == "C"
    assert s.twist == "T"


def test_myth_format_loads_with_stage_accents_default():
    fmt = format_registry.get("myth")
    assert fmt is not None
    assert fmt.label == "Myth vs Fact"
    assert fmt.caption_styles == ["highlight", "plain"]
    assert fmt.duration_range == (38, 50)
    assert fmt.pacing_wps_range == (2.5, 3.0)
    cfg = RenderConfig.resolve(fmt)
    assert cfg.stage_accents == {}


def test_stage_accents_override_reaches_render_config():
    cfg = RenderConfig.resolve(None, {"stage_accents": {"message": "0xFF00FFFF"}})
    assert cfg.stage_accents == {"message": "0xFF00FFFF"}


def test_myth_stage_accent_applies_to_message_line_caption():
    cfg = RenderConfig.resolve(None, {"stage_accents": {"message": "0xFF00FFFF"}})
    img = _render_caption_frame(
        ["one", "two"],
        highlighted_idx=0,
        font_size=64,
        render_config=cfg,
        highlight_colour=cfg.stage_accents.get("message"),
    )
    assert (255, 0, 255, 255) in set(img.get_flattened_data())


def test_parse_script_folds_claim_facts_and_twist():
    text = """TITLE: T
DURATION: 40
WORD COUNT: 100
PACING: 2.5
[HOOK - 3s]
"H"

[CLAIM - Ns]
"C"

[FACT - 7s]
"F1"

[FACT - Ns]
"F2"

[FACT - 7s]
"F3"

[TWIST - 5s]
"T"

[METAPHOR - 2s]
"M"

[CONCLUSION - 5s]
"O"
"""
    s = parse_script(text)
    assert s.fact_count == 3
    assert s.claim == "C"
    assert s.twist == "T"
    assert s.message_lines == ["C", "F1", "F2", "F3", "T"]
