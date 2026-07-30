from __future__ import annotations

from typing import ClassVar

import pytest
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.result import Ok

from shorts_creator.pipeline.pipeline import ReelPipeline
from shorts_creator.pipeline.render_config import RenderConfig
from shorts_creator.pipeline.script_parser import ParsedScript

_NARRATED_SCRIPT = ParsedScript(
    title="Test",
    duration_seconds=20.0,
    word_count=10,
    pacing_wps=2.0,
    hook="Hook",
    hook_seconds=3.0,
    message_lines=["Message one", "Message two"],
    message_seconds=8.0,
    metaphor="Metaphor",
    metaphor_seconds=3.0,
    conclusion="Conclusion",
    conclusion_seconds=3.0,
    emotional_arc=[],
    parallel_structure="",
    hook_score="",
    section_names=["hook", "message", "message", "metaphor", "conclusion"],
)

_TWO_LINE_SCRIPT = ParsedScript(
    title="Two",
    duration_seconds=5.0,
    word_count=10,
    pacing_wps=2.0,
    hook="Hook",
    hook_seconds=3.0,
    message_lines=["Message one"],
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

_NARRATED_LINE_DATA = [
    ("line_0.wav", 3.0, [{"word": "H", "start": 0.0, "end": 3.0}]),
    ("line_1.wav", 2.0, [{"word": "A", "start": 0.0, "end": 2.0}]),
    ("line_2.wav", 2.0, [{"word": "B", "start": 0.0, "end": 2.0}]),
    ("line_3.wav", 2.0, [{"word": "C", "start": 0.0, "end": 2.0}]),
    ("line_4.wav", 2.0, [{"word": "D", "start": 0.0, "end": 2.0}]),
]

_TWO_LINE_DATA = [
    ("line_0.wav", 3.0, [{"word": "H", "start": 0.0, "end": 3.0}]),
    ("line_1.wav", 2.0, [{"word": "A", "start": 0.0, "end": 2.0}]),
]

_LEGACY_SCRIPT = ParsedScript(
    title="Legacy",
    duration_seconds=10.0,
    word_count=10,
    pacing_wps=2.0,
    hook="Hook",
    hook_seconds=3.0,
    message_lines=["Line one", "Line two", "Line three"],
    message_seconds=6.0,
    metaphor="Metaphor",
    metaphor_seconds=2.0,
    conclusion="Conclusion",
    conclusion_seconds=2.0,
    emotional_arc=[],
    parallel_structure="",
    hook_score="",
)

_LEGACY_LINE_DATA = [
    ("line_0.wav", 3.0, [{"word": "H", "start": 0.0, "end": 3.0}]),
    ("line_1.wav", 2.0, [{"word": "A", "start": 0.0, "end": 2.0}]),
    ("line_2.wav", 2.0, [{"word": "B", "start": 0.0, "end": 2.0}]),
    ("line_3.wav", 2.0, [{"word": "C", "start": 0.0, "end": 2.0}]),
]


class _FakeTimeline:
    instances: ClassVar[list[_FakeTimeline]] = []

    def __init__(self):
        self.clips = []
        self.overlays = []
        self.audios = []
        self.fade_in = None
        self.fade_out = None
        self.encode = None
        _FakeTimeline.instances.append(self)

    def add_clip(self, asset, **kwargs):
        self.clips.append(asset)
        return self

    def add_overlay(self, asset, **kwargs):
        self.overlays.append((asset, kwargs))
        return self

    def add_audio(self, asset, **kwargs):
        self.audios.append((asset, kwargs))
        return self

    def set_fade_in(self, duration):
        self.fade_in = duration
        return self

    def set_fade_out(self, duration):
        self.fade_out = duration
        return self

    def set_encode(self, spec):
        self.encode = spec
        return self

    def to_params(self):
        return {"clips": len(self.clips), "overlays": len(self.overlays)}

    async def render(self, processor, progress_callback=None):
        progress_callback(0.5)
        progress_callback(1.0)
        return Ok(MediaAsset(mime_type="video/mp4", provider="test", bytes_data=b"vid"))


def _patch_render_harness(monkeypatch):
    async def fake_group_by_thought(line, words, llm):
        return [words]

    def fake_hook_group(words, target_size=1):
        return [words]

    async def fake_segments(segments, fps):
        return [("/tmp/bg.mp4", 0, segments[-1][2])]

    async def recorder(stage, progress, message):
        pass

    captured = []

    def fake_caption_clip(*args, **kwargs):
        captured.append(kwargs.get("highlight_colour"))

    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_by_thought", fake_group_by_thought
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_for_hook_display", fake_hook_group
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.caption_text._render_hook_clip", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.caption_text._render_caption_clip", fake_caption_clip
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.ReelPipeline._extract_screenshots", lambda self: None
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.ReelPipeline._transcode_720p", lambda self: None
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.ReelPipeline._make_black_base", lambda self, *a: None
    )
    monkeypatch.setattr("shorts_creator.pipeline.outro.generate_outro_clip", lambda *a, **k: None)
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.stock_video._probe_duration", lambda *a, **k: 3.0
    )
    monkeypatch.setattr("lexigram.multimedia.timeline.Timeline", _FakeTimeline)
    _FakeTimeline.instances = []

    async def run_pipeline(script, line_data, stage_accents):
        async def fake_narration(lines):
            return list(line_data)

        out_path = str(monkeypatch._tmp_path / "out.mp4")
        pipeline = ReelPipeline(
            output=out_path,
            progress_callback=recorder,
            render_config=RenderConfig(stage_accents=stage_accents),
        )
        pipeline.script = script
        pipeline.run_dir = str(monkeypatch._tmp_path)
        pipeline._synthesize_narration = fake_narration
        pipeline._fetch_background_segments = fake_segments

        ok = await pipeline.run()
        assert ok is True
        return list(captured)

    return run_pipeline


@pytest.mark.asyncio
async def test_message_accent_applies_to_message_lines_only(tmp_path, monkeypatch):
    monkeypatch._tmp_path = tmp_path
    run_pipeline = _patch_render_harness(monkeypatch)

    colours = await run_pipeline(_NARRATED_SCRIPT, _NARRATED_LINE_DATA, {"message": "0x22D3EEFF"})

    assert colours == ["0x22D3EEFF", "0x22D3EEFF", None, None]


@pytest.mark.asyncio
async def test_metaphor_and_conclusion_accents_land_on_their_lines(tmp_path, monkeypatch):
    monkeypatch._tmp_path = tmp_path
    run_pipeline = _patch_render_harness(monkeypatch)

    colours = await run_pipeline(
        _NARRATED_SCRIPT,
        _NARRATED_LINE_DATA,
        {"metaphor": "0x34D399FF", "conclusion": "0xFB7185FF"},
    )

    assert colours == [None, None, "0x34D399FF", "0xFB7185FF"]


@pytest.mark.asyncio
async def test_hook_accent_applies_to_no_caption_lines(tmp_path, monkeypatch):
    monkeypatch._tmp_path = tmp_path
    run_pipeline = _patch_render_harness(monkeypatch)

    colours = await run_pipeline(
        _NARRATED_SCRIPT,
        _NARRATED_LINE_DATA,
        {"hook": "0xFF00FFFF", "unknown_section": "0x22D3EEFF"},
    )

    assert colours == [None, None, None, None]


@pytest.mark.asyncio
async def test_two_line_format_keeps_accent_on_its_single_caption_line(tmp_path, monkeypatch):
    monkeypatch._tmp_path = tmp_path
    run_pipeline = _patch_render_harness(monkeypatch)

    colours = await run_pipeline(_TWO_LINE_SCRIPT, _TWO_LINE_DATA, {"message": "0xFF00FFFF"})

    assert colours == ["0xFF00FFFF"]


@pytest.mark.asyncio
async def test_script_without_section_names_gets_no_accents(tmp_path, monkeypatch):
    monkeypatch._tmp_path = tmp_path
    run_pipeline = _patch_render_harness(monkeypatch)

    colours = await run_pipeline(
        _LEGACY_SCRIPT,
        _LEGACY_LINE_DATA,
        {"message": "0xFF00FFFF", "metaphor": "0x34D399FF"},
    )

    assert colours == [None, None, None]


@pytest.mark.asyncio
async def test_old_string_index_keys_no_longer_take_effect(tmp_path, monkeypatch):
    monkeypatch._tmp_path = tmp_path
    run_pipeline = _patch_render_harness(monkeypatch)

    colours = await run_pipeline(
        _NARRATED_SCRIPT,
        _NARRATED_LINE_DATA,
        {"0": "0x22D3EEFF", "1": "0xFF00FFFF"},
    )

    assert colours == [None, None, None, None]
