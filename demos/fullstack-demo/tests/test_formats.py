import tempfile
from pathlib import Path

import pytest

from shorts_creator.contracts.errors import FormatContractError
from shorts_creator.formats import registry
from shorts_creator.formats.loader import (
    load_format,
    parse_format_md,
    validate_format_contract,
)
from shorts_creator.formats.registry import FormatRegistry
from shorts_creator.pipeline.render_config import RenderConfig

GOOD_FRONTMATTER = """---
name: speech
label: Speech
description: Plain spoken-word captions
caption_styles:
  - highlight
  - plain
default_caption_style: highlight
---
"""

BAD_FRONTMATTER = "no frontmatter here"


class TestFormatRegistry:
    def test_singleton_has_narrated(self):
        assert registry.has("narrated")

    def test_narrated_styles(self):
        fmt = registry.get("narrated")
        assert fmt is not None
        assert fmt.caption_styles == ["highlight", "plain"]
        assert fmt.default_caption_style == "highlight"

    def test_narrated_duration_and_pacing_ranges(self):
        fmt = registry.get("narrated")
        assert fmt is not None
        assert fmt.duration_range == (38, 50)
        assert fmt.pacing_wps_range == (2.5, 3.0)

    def test_choices(self):
        choices = registry.available
        assert len(choices) >= 1
        narrated = next(c for c in choices if c.name == "narrated")
        assert narrated.label == "Narrated"

    def test_get_unknown_returns_none(self):
        assert registry.get("nonexistent") is None

    def test_load_from_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            fmt_dir = Path(tmp) / "speech"
            fmt_dir.mkdir()
            (fmt_dir / "FORMAT.md").write_text(GOOD_FRONTMATTER, encoding="utf-8")
            r = FormatRegistry()
            assert r.load(tmp) == 1
            assert r.has("speech")
            assert r.get("speech").caption_styles == ["highlight", "plain"]

    def test_load_skips_broken_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            fmt_dir = Path(tmp) / "broken"
            fmt_dir.mkdir()
            (fmt_dir / "FORMAT.md").write_text(BAD_FRONTMATTER, encoding="utf-8")
            r = FormatRegistry()
            assert r.load(tmp) == 0
            assert not r.has("broken")


class TestLoadFormat:
    def test_parse_md_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "FORMAT.md"
            path.write_text(GOOD_FRONTMATTER, encoding="utf-8")
            data = parse_format_md(path)
            assert data["name"] == "speech"
            assert data["default_caption_style"] == "highlight"

    def test_load_missing_frontmatter_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "FORMAT.md"
            path.write_text(BAD_FRONTMATTER, encoding="utf-8")
            with pytest.raises(ValueError):
                load_format(path)


class TestCaptionlessStyles:
    def test_explicit_empty_styles_stay_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "FORMAT.md"
            path.write_text(
                """---
name: beat
label: Beat
description: Caption-less
caption_styles: []
default_caption_style: ""
---
""",
                encoding="utf-8",
            )
            fmt = load_format(path)
            assert fmt.caption_styles == []
            assert fmt.default_caption_style == ""

    def test_missing_styles_key_defaults_to_highlight(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "FORMAT.md"
            path.write_text(
                """---
name: plain
label: Plain
description: Plain
---
""",
                encoding="utf-8",
            )
            fmt = load_format(path)
            assert fmt.caption_styles == ["highlight"]
            assert fmt.default_caption_style == "highlight"


class TestTopNFormat:
    def test_singleton_has_topn(self):
        assert registry.has("topn")

    def test_topn_definition_shape(self):
        fmt = registry.get("topn")
        assert fmt is not None
        assert fmt.label == "Top N"
        assert fmt.caption_styles == []
        assert fmt.default_caption_style == ""
        assert fmt.duration_range == (35, 50)
        assert fmt.pacing_wps_range == (2.4, 3.0)

    def test_topn_contract(self):
        fmt = registry.get("topn")
        assert fmt is not None
        side = fmt.to_contract_side()
        assert side.requires_script == frozenset({"hook", "top_items", "conclusion"})
        assert "music_beat" in side.requires_pipeline
        assert "captions" not in side.requires_pipeline
        assert side.requires_assets == frozenset({"music"})

    def test_topn_strict_directory_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            fmt_dir = Path(tmp) / "topn"
            fmt_dir.mkdir()
            (fmt_dir / "FORMAT.md").write_text(
                """---
name: topn
label: Top N
description: A ranked list of 5 concrete items for the topic, driven by a beat-locked music bed.
caption_styles: []
default_caption_style: ""
duration_range: [35, 50]
pacing_wps_range: [2.4, 3.0]
requires:
  script: [hook, top_items, conclusion]
  voice: [tts_story]
  pipeline: [tts_story, word_timing, background, outro, music_beat]
  assets: [music]
objectives: []
---
""",
                encoding="utf-8",
            )
            r = FormatRegistry()
            assert r.load(tmp, strict=True) == 1
            assert r.has("topn")


class TestStepsFormat:
    def test_singleton_has_steps(self):
        assert registry.has("steps")

    def test_steps_definition_shape(self):
        fmt = registry.get("steps")
        assert fmt is not None
        assert fmt.label == "Steps"
        assert fmt.caption_styles == []
        assert fmt.default_caption_style == ""
        assert fmt.duration_range == (38, 50)
        assert fmt.pacing_wps_range == (2.5, 3.0)
        assert fmt.defaults.get("ranked_number_scale") == 1.4

    def test_steps_contract(self):
        fmt = registry.get("steps")
        assert fmt is not None
        side = fmt.to_contract_side()
        assert side.requires_script == frozenset({"hook", "top_items"})
        assert "music_beat" in side.requires_pipeline
        assert "captions" in side.requires_pipeline


def test_format_parses_layout_and_palette(tmp_path):
    md = tmp_path / "styled" / "FORMAT.md"
    md.parent.mkdir()
    md.write_text(
        "---\n"
        "name: styled\n"
        "label: Styled\n"
        "caption_styles: [highlight]\n"
        "layout:\n"
        "  anchor: lower_third\n"
        "  block_width_pct: [60, 95]\n"
        "  numbered_scale: [1.2, 2.5]\n"
        "  pill_per_word: true\n"
        "palette:\n"
        "  highlight_colour: 0xFF00FFAA\n"
        "  pill_bg_colour: 0x000000FF\n"
        "---\n",
        encoding="utf-8",
    )
    fmt = load_format(md)
    assert fmt.layout == {
        "anchor": "lower_third",
        "block_width_pct": [60, 95],
        "numbered_scale": [1.2, 2.5],
        "pill_per_word": True,
    }
    assert fmt.palette == {"highlight_colour": "0xFF00FFAA", "pill_bg_colour": "0x000000FF"}


def test_format_rejects_unknown_anchor(tmp_path):
    from shorts_creator.contracts.errors import FormatContractError

    md = tmp_path / "bad" / "FORMAT.md"
    md.parent.mkdir()
    md.write_text(
        "---\nname: bad\nlabel: Bad\nlayout:\n  anchor: upper_third\n---\n",
        encoding="utf-8",
    )
    try:
        load_format(md)
    except FormatContractError:
        pass
    else:
        raise AssertionError("expected FormatContractError for unknown anchor")


def test_format_rejects_bad_slider_range(tmp_path):
    from shorts_creator.contracts.errors import FormatContractError

    md = tmp_path / "bad2" / "FORMAT.md"
    md.parent.mkdir()
    md.write_text(
        "---\nname: bad2\nlabel: Bad2\nlayout:\n  block_width_pct: [95, 60]\n---\n",
        encoding="utf-8",
    )
    try:
        load_format(md)
    except FormatContractError:
        pass
    else:
        raise AssertionError("expected FormatContractError for inverted range")


class TestDefaultsBlock:
    def test_defaults_block_parses_and_validates(self, tmp_path):
        md = tmp_path / "f" / "FORMAT.md"
        md.parent.mkdir()
        md.write_text(
            "---\nname: t1\ncaption_styles: [highlight]\ndefaults:\n"
            "  caption_font_size: 64\n  music_volume: 0.1\n"
            "  loudness_target_lufs: -14\n---\n"
            "body ignored\n",
            encoding="utf-8",
        )
        data = parse_format_md(md)
        validate_format_contract(data)
        assert data["defaults"] == {
            "caption_font_size": 64,
            "music_volume": 0.1,
            "loudness_target_lufs": -14,
        }

    def test_defaults_block_rejects_unknown_keys(self, tmp_path):
        md = tmp_path / "f" / "FORMAT.md"
        md.parent.mkdir()
        md.write_text(
            "---\nname: t1\ncaption_styles: [highlight]\ndefaults:\n  not_a_render_key: 1\n---\n",
            encoding="utf-8",
        )
        with pytest.raises(FormatContractError):
            validate_format_contract(parse_format_md(md))


class TestSectionNames:
    def test_claim_fact_twist_fold_to_message_labels(self):
        from shorts_creator.pipeline.script_parser import to_pipeline_script

        saved = {
            "title": "Myth",
            "total_duration": 30,
            "sections": [
                {"name": "hook", "text": "H", "duration_seconds": 3},
                {"name": "claim", "text": "C", "duration_seconds": 4},
                {"name": "fact", "text": "F1", "duration_seconds": 7},
                {"name": "fact", "text": "F2", "duration_seconds": 7},
                {"name": "twist", "text": "T", "duration_seconds": 5},
                {"name": "conclusion", "text": "O", "duration_seconds": 4},
            ],
        }
        s = to_pipeline_script(saved)
        assert s.section_names == [
            "hook",
            "message",
            "message",
            "message",
            "message",
            "metaphor",
            "conclusion",
        ]

    def test_legacy_without_sections_infers_positions(self):
        from shorts_creator.pipeline.script_parser import to_pipeline_script

        saved = {
            "title": "Legacy",
            "duration_seconds": 12.0,
            "hook": "Hook",
            "message_lines": ["A", "B", "C"],
        }
        s = to_pipeline_script(saved)
        assert s.section_names == [
            "hook",
            "hook",
            "message",
            "conclusion",
            "metaphor",
            "conclusion",
        ]


class TestDefaultsResolve:
    def _load(self, tmp_path, defaults_block):
        md = tmp_path / "t" / "FORMAT.md"
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text(
            "---\nname: t\ncaption_styles: [highlight]\n" + defaults_block + "---\n",
            encoding="utf-8",
        )
        return load_format(md)

    def test_defaults_block_flows_into_resolved_config(self, tmp_path):
        fmt = self._load(
            tmp_path,
            "defaults:\n  caption_font_size: 64\n  music_volume: 0.1\n",
        )
        cfg = RenderConfig.resolve(fmt)
        assert cfg.caption_font_size == 64
        assert cfg.music_volume == 0.1

    def test_project_overrides_beat_format_defaults(self, tmp_path):
        fmt = self._load(tmp_path, "defaults:\n  music_volume: 0.1\n")
        cfg = RenderConfig.resolve(fmt, {"layout": {"music_volume": 0.3}})
        assert cfg.music_volume == 0.3

    def test_phase_two_defaults_flow_into_resolved_config(self, tmp_path):
        fmt = self._load(tmp_path, "defaults:\n  loudness_target_lufs: -14\n")
        cfg = RenderConfig.resolve(fmt)
        assert cfg.loudness_target_lufs == -14
        assert cfg.audio_normalize is True

    def test_int_form_colour_default_normalised_like_palette(self, tmp_path):
        fmt = self._load(tmp_path, "defaults:\n  caption_highlight_colour: 0x7C5CFAFF\n")
        cfg = RenderConfig.resolve(fmt)
        assert cfg.caption_highlight_colour == "0x7C5CFAFF"

    @pytest.mark.parametrize(
        "bad_defaults",
        [
            "anchor: top_left",
            "background_motion: spin",
            "caption_uppercase: 1",
            "caption_highlight_colour: red",
            "music_volume: loud",
            "section_holds:\n    intro: hold",
        ],
    )
    def test_defaults_value_level_rejection(self, tmp_path, bad_defaults):
        with pytest.raises(FormatContractError):
            self._load(tmp_path, f"defaults:\n  {bad_defaults}\n")
