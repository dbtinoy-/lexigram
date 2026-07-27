from __future__ import annotations

import asyncio
import os
import subprocess
from typing import ClassVar

import pytest
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.result import Ok

from shorts_creator.pipeline.pipeline import FADE_OUT_SECONDS, OUTRO_DEFAULT_PATH, ReelPipeline
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

_WORDS = [{"word": "A", "start": 0.0, "end": 3.0}]
_LINE_DATA = [
    ("line_0.wav", 3.0, _WORDS),
    ("line_1.wav", 2.0, [{"word": "B", "start": 0.0, "end": 2.0}]),
]


def test_make_black_base_command_shape(tmp_path, monkeypatch):
    captured = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["kwargs"] = kwargs

    monkeypatch.setattr(subprocess, "run", fake_run)
    pipeline = ReelPipeline()
    pipeline.temp_dir = str(tmp_path)

    pipeline._make_black_base(os.path.join(str(tmp_path), "black_base.mp4"), 262, 30.0)

    argv = captured["argv"]
    assert argv[0] == "ffmpeg"
    assert argv[1] == "-y"
    assert argv[2:5] == ["-f", "lavfi", "-i"]
    assert argv[5] == "color=black:size=1080x1920:rate=30.0"
    assert argv[6:8] == ["-t", "8.733333333333333"]
    assert argv[8:11] == ["-c:v", "libx264", "-pix_fmt"]
    assert argv[11] == "yuv420p"
    assert argv[12] == os.path.join(str(tmp_path), "black_base.mp4")
    assert captured["kwargs"].get("check") is True


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
        assert progress_callback is not None
        progress_callback(0.5)
        progress_callback(1.0)
        return Ok(MediaAsset(mime_type="video/mp4", provider="test", bytes_data=b"vid"))


@pytest.mark.asyncio
async def test_run_ffmpeg_uses_compose_plan_and_writes_output(tmp_path, monkeypatch):
    async def fake_narration(lines):
        return list(_LINE_DATA)

    async def fake_segments(segments, fps):
        return [("/tmp/bg.mp4", 0, 150)]

    async def fake_group_by_thought(line, words, llm):
        return [words]

    def fake_hook_group(words, target_size=1):
        return [words]

    captured_stages = []

    async def recorder(stage, progress, message):
        captured_stages.append((stage, progress))

    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_by_thought", fake_group_by_thought
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_for_hook_display", fake_hook_group
    )
    monkeypatch.setattr("shorts_creator.pipeline.pipeline._render_hook_clip", lambda *a, **k: None)
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline._render_caption_clip", lambda *a, **k: None
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
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.generate_outro_clip", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.stock_video._probe_duration", lambda *a, **k: 3.0
    )
    monkeypatch.setattr("lexigram.multimedia.timeline.Timeline", _FakeTimeline)

    out_path = str(tmp_path / "out.mp4")
    pipeline = ReelPipeline(output=out_path, progress_callback=recorder)
    pipeline.script = _SCRIPT
    pipeline.run_dir = str(tmp_path)
    pipeline._synthesize_narration = fake_narration
    pipeline._fetch_background_segments = fake_segments

    ok = await pipeline.run()

    assert ok is True
    with open(out_path, "rb") as fh:  # noqa: ASYNC230
        assert fh.read() == b"vid"
    assert (os.stat(out_path).st_mode & 0o777) == 0o644
    assert pipeline.duration_frames == 90 + 60 + 90
    assert _FakeTimeline.instances[-1].fade_out == FADE_OUT_SECONDS

    stages = [s for s in captured_stages]
    assert ("outputs", 0.0) in stages and ("outputs", 1.0) in stages
    assert ("project", 0.0) in stages and ("project", 1.0) in stages
    assert ("timeline", 0.0) in stages
    assert ("timeline", 0.25) in stages
    assert ("timeline", 0.3) in stages
    assert ("timeline", 0.4) in stages
    assert ("timeline", 1.0) in stages
    assert ("render", 1.0) in stages
    assert ("finalize", 0.0) in stages
    assert ("finalize", 0.5) in stages
    assert ("finalize", 1.0) in stages
    assert os.path.exists(os.path.join(str(tmp_path), "timeline_recipe.json"))


@pytest.mark.asyncio
async def test_run_ffmpeg_generates_fresh_outro_when_text_set(tmp_path, monkeypatch):
    async def fake_narration(lines):
        return list(_LINE_DATA)

    async def fake_segments(segments, fps):
        return [("/tmp/bg.mp4", 0, 150)]

    async def fake_group_by_thought(line, words, llm):
        return [words]

    def fake_hook_group(words, target_size=1):
        return [words]

    async def recorder(stage, progress, message):
        pass

    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_by_thought", fake_group_by_thought
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_for_hook_display", fake_hook_group
    )
    monkeypatch.setattr("shorts_creator.pipeline.pipeline._render_hook_clip", lambda *a, **k: None)
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline._render_caption_clip", lambda *a, **k: None
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
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.stock_video._probe_duration", lambda *a, **k: 3.0
    )
    monkeypatch.setattr("lexigram.multimedia.timeline.Timeline", _FakeTimeline)
    _FakeTimeline.instances = []

    generated_outros = []

    def fake_generate(output_path, width, height, text="Thanks for watching"):
        generated_outros.append((output_path, text))
        with open(output_path, "wb") as fh:
            fh.write(b"outro")

    def fake_fit(src, dst, *a, **k):
        with open(dst, "wb") as fh:
            fh.write(b"fitted")

    monkeypatch.setattr("shorts_creator.pipeline.pipeline.generate_outro_clip", fake_generate)
    monkeypatch.setattr("shorts_creator.pipeline.pipeline._fit_clip_to_canvas", fake_fit)

    out_path = str(tmp_path / "out.mp4")
    pipeline = ReelPipeline(output=out_path, progress_callback=recorder, outro_text="Custom outro")
    pipeline.script = _SCRIPT
    pipeline.run_dir = str(tmp_path)
    pipeline._synthesize_narration = fake_narration
    pipeline._fetch_background_segments = fake_segments

    ok = await pipeline.run()

    assert ok is True
    assert len(generated_outros) == 1
    outro_path, text = generated_outros[0]
    assert os.path.basename(outro_path) == "outro_default.mp4"
    assert outro_path != OUTRO_DEFAULT_PATH
    assert outro_path.startswith("/tmp/")
    assert text == "Custom outro"


@pytest.mark.asyncio
async def test_run_ffmpeg_overlays_outro_text_on_custom_outro_clip(tmp_path, monkeypatch):
    async def fake_narration(lines):
        return list(_LINE_DATA)

    async def fake_segments(segments, fps):
        return [("/tmp/bg.mp4", 0, 150)]

    async def fake_group_by_thought(line, words, llm):
        return [words]

    def fake_hook_group(words, target_size=1):
        return [words]

    async def recorder(stage, progress, message):
        pass

    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_by_thought", fake_group_by_thought
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_for_hook_display", fake_hook_group
    )
    monkeypatch.setattr("shorts_creator.pipeline.pipeline._render_hook_clip", lambda *a, **k: None)
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline._render_caption_clip", lambda *a, **k: None
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
    monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline.cleanup", lambda self: None)
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.stock_video._probe_duration", lambda *a, **k: 3.0
    )
    monkeypatch.setattr("lexigram.multimedia.timeline.Timeline", _FakeTimeline)
    _FakeTimeline.instances = []

    outro_asset = str(tmp_path / "custom_outro.mp4")
    with open(outro_asset, "wb") as fh:  # noqa: ASYNC230
        fh.write(b"custom")

    def fake_fit(src, dst, *a, **k):
        with open(dst, "wb") as fh:
            fh.write(b"fitted")

    def fake_text_overlay(text, out_path, *a, **k):
        with open(out_path, "wb") as fh:
            fh.write(b"text-overlay")

    monkeypatch.setattr("shorts_creator.pipeline.pipeline._fit_clip_to_canvas", fake_fit)
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline._render_outro_text_clip", fake_text_overlay
    )

    captured = {}

    def fake_build_plan(*args, **kwargs):
        captured.update(kwargs)
        from lexigram.contracts.multimedia.types import EncodeSpec, MediaAsset

        from shorts_creator.pipeline.compose import ComposePlan

        return ComposePlan(
            base_asset=MediaAsset(
                mime_type="video/mp4", provider="local-http", uri="file:///x.mp4"
            ),
            overlays=[],
            audio_layers=[],
            fade_in=0.5,
            fade_out=0.5,
            encode=EncodeSpec(codec="hevc_nvenc", bitrate="10M", resolution="1080x1920", fps=30),
            total_frames=1,
            narration_end_frames=1,
        )

    monkeypatch.setattr("shorts_creator.pipeline.compose.build_compose_plan", fake_build_plan)

    from shorts_creator.models.asset_bundle import AssetBundle

    out_path = str(tmp_path / "out.mp4")
    pipeline = ReelPipeline(
        output=out_path,
        progress_callback=recorder,
        outro_text="Custom outro",
        assets=AssetBundle(outro_clip_path=outro_asset),
    )
    pipeline.script = _SCRIPT
    pipeline.run_dir = str(tmp_path)
    pipeline._synthesize_narration = fake_narration
    pipeline._fetch_background_segments = fake_segments

    ok = await pipeline.run()

    assert ok is True
    assert (
        captured.get("outro_text_path")
        and os.path.basename(captured["outro_text_path"]) == "outro_text.mov"
    )
    with open(captured["outro_text_path"], "rb") as fh:  # noqa: ASYNC230
        assert fh.read() == b"text-overlay"


@pytest.mark.asyncio
async def test_run_ffmpeg_skips_text_overlay_for_default_outro(tmp_path, monkeypatch):
    async def fake_narration(lines):
        return list(_LINE_DATA)

    async def fake_segments(segments, fps):
        return [("/tmp/bg.mp4", 0, 150)]

    async def fake_group_by_thought(line, words, llm):
        return [words]

    def fake_hook_group(words, target_size=1):
        return [words]

    async def recorder(stage, progress, message):
        pass

    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_by_thought", fake_group_by_thought
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_for_hook_display", fake_hook_group
    )
    monkeypatch.setattr("shorts_creator.pipeline.pipeline._render_hook_clip", lambda *a, **k: None)
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline._render_caption_clip", lambda *a, **k: None
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
    monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline.cleanup", lambda self: None)
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.stock_video._probe_duration", lambda *a, **k: 3.0
    )
    monkeypatch.setattr("lexigram.multimedia.timeline.Timeline", _FakeTimeline)
    _FakeTimeline.instances = []

    generated_outros = []

    def fake_generate(output_path, width, height, text="Thanks for watching"):
        generated_outros.append((output_path, text))
        with open(output_path, "wb") as fh:
            fh.write(b"outro")

    def fake_fit(src, dst, *a, **k):
        with open(dst, "wb") as fh:
            fh.write(b"fitted")

    def fake_text_overlay(text, out_path, *a, **k):
        with open(out_path, "wb") as fh:
            fh.write(b"text-overlay")

    monkeypatch.setattr("shorts_creator.pipeline.pipeline.generate_outro_clip", fake_generate)
    monkeypatch.setattr("shorts_creator.pipeline.pipeline._fit_clip_to_canvas", fake_fit)
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline._render_outro_text_clip", fake_text_overlay
    )

    captured = {}

    def fake_build_plan(*args, **kwargs):
        captured.update(kwargs)
        from lexigram.contracts.multimedia.types import EncodeSpec, MediaAsset

        from shorts_creator.pipeline.compose import ComposePlan

        return ComposePlan(
            base_asset=MediaAsset(
                mime_type="video/mp4", provider="local-http", uri="file:///x.mp4"
            ),
            overlays=[],
            audio_layers=[],
            fade_in=0.5,
            fade_out=0.5,
            encode=EncodeSpec(codec="hevc_nvenc", bitrate="10M", resolution="1080x1920", fps=30),
            total_frames=1,
            narration_end_frames=1,
        )

    monkeypatch.setattr("shorts_creator.pipeline.compose.build_compose_plan", fake_build_plan)

    out_path = str(tmp_path / "out.mp4")
    pipeline = ReelPipeline(
        output=out_path,
        progress_callback=recorder,
        outro_text="Thanks for watching",
    )
    pipeline.script = _SCRIPT
    pipeline.run_dir = str(tmp_path)
    pipeline._synthesize_narration = fake_narration
    pipeline._fetch_background_segments = fake_segments

    ok = await pipeline.run()

    assert ok is True
    assert len(generated_outros) == 1
    assert captured.get("outro_text_path", None) in ("", None)


@pytest.mark.asyncio
async def test_run_ffmpeg_fetches_segment_backgrounds(tmp_path, monkeypatch):
    async def fake_narration(lines):
        return list(_LINE_DATA)

    async def fake_group_by_thought(line, words, llm):
        return [words]

    def fake_hook_group(words, target_size=1):
        return [words]

    async def recorder(stage, progress, message):
        pass

    fetched = []

    async def fake_fetch(query, out_path, min_seconds, **kwargs):
        fetched.append((query, min_seconds))
        return True

    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_by_thought", fake_group_by_thought
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_for_hook_display", fake_hook_group
    )
    monkeypatch.setattr("shorts_creator.pipeline.pipeline._render_hook_clip", lambda *a, **k: None)
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline._render_caption_clip", lambda *a, **k: None
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
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.generate_outro_clip", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.stock_video._probe_duration", lambda *a, **k: 3.0
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.stock_video.fetch_background_video", fake_fetch
    )
    monkeypatch.setattr("lexigram.multimedia.timeline.Timeline", _FakeTimeline)
    _FakeTimeline.instances = []

    out_path = str(tmp_path / "out.mp4")
    pipeline = ReelPipeline(
        output=out_path,
        progress_callback=recorder,
        bg_source="api",
        background_queries=["q1", "q2"],
    )
    pipeline.script = _SCRIPT
    pipeline.run_dir = str(tmp_path)
    pipeline._synthesize_narration = fake_narration

    ok = await pipeline.run()

    assert ok is True
    assert len(fetched) == 2
    assert all(q in ("q1", "q2") for q, _ in fetched)
    assert fetched[0][1] == pytest.approx(3.0)
    assert fetched[1][1] == pytest.approx(2.0)
    bg = [o for o in _FakeTimeline.instances[-1].overlays if "background_stock" in o[0].uri]
    assert len(bg) == 2
    assert sorted(kw["start"] for o, kw in bg) == [0.0, 3.0]
    assert sorted(kw["end"] for o, kw in bg) == [3.0, 5.0]


@pytest.mark.asyncio
async def test_background_segment_queries_come_from_line_sentiment(tmp_path, monkeypatch):
    from dataclasses import replace

    script = replace(
        _SCRIPT,
        hook="Anxious days pass quietly",
        message_lines=["Push through with discipline"],
        conclusion="Rest and peace follow",
    )

    async def fake_narration(lines):
        return list(_LINE_DATA)

    async def fake_group_by_thought(line, words, llm):
        return [words]

    def fake_hook_group(words, target_size=1):
        return [words]

    async def recorder(stage, progress, message):
        pass

    fetched = []

    async def fake_fetch(query, out_path, min_seconds, **kwargs):
        fetched.append(query)
        return True

    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_by_thought", fake_group_by_thought
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_for_hook_display", fake_hook_group
    )
    monkeypatch.setattr("shorts_creator.pipeline.pipeline._render_hook_clip", lambda *a, **k: None)
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline._render_caption_clip", lambda *a, **k: None
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
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.generate_outro_clip", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.stock_video._probe_duration", lambda *a, **k: 3.0
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.stock_video.fetch_background_video", fake_fetch
    )
    monkeypatch.setattr("lexigram.multimedia.timeline.Timeline", _FakeTimeline)
    _FakeTimeline.instances = []

    pool = ["calm forest river", "sunrise ocean waves", "meditation quiet"]
    out_path = str(tmp_path / "out.mp4")
    pipeline = ReelPipeline(
        output=out_path,
        progress_callback=recorder,
        bg_source="api",
        background_queries=pool,
    )
    pipeline.script = script
    pipeline.run_dir = str(tmp_path)
    pipeline._synthesize_narration = fake_narration

    ok = await pipeline.run()

    assert ok is True
    assert fetched == ["calm forest river", "sunrise ocean waves"]


@pytest.mark.asyncio
async def test_run_ffmpeg_segment_failures_fall_back_to_full_gradient(tmp_path, monkeypatch):
    async def fake_narration(lines):
        return list(_LINE_DATA)

    async def fake_group_by_thought(line, words, llm):
        return [words]

    def fake_hook_group(words, target_size=1):
        return [words]

    async def recorder(stage, progress, message):
        pass

    async def fake_fetch(query, out_path, min_seconds, **kwargs):
        return False

    gradient_calls = []

    def fake_generate(img_path, width, height):
        gradient_calls.append((img_path, width, height))

    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_by_thought", fake_group_by_thought
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_for_hook_display", fake_hook_group
    )
    monkeypatch.setattr("shorts_creator.pipeline.pipeline._render_hook_clip", lambda *a, **k: None)
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline._render_caption_clip", lambda *a, **k: None
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
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.generate_outro_clip", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.stock_video._probe_duration", lambda *a, **k: 3.0
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.stock_video.fetch_background_video", fake_fetch
    )
    monkeypatch.setattr("shorts_creator.pipeline.pipeline.generate_background", fake_generate)
    monkeypatch.setattr("shorts_creator.pipeline.pipeline._looped_gradient_video", lambda *a: None)
    monkeypatch.setattr("lexigram.multimedia.timeline.Timeline", _FakeTimeline)
    _FakeTimeline.instances = []

    out_path = str(tmp_path / "out.mp4")
    pipeline = ReelPipeline(
        output=out_path,
        progress_callback=recorder,
        bg_source="api",
        background_queries=["q1", "q2"],
    )
    pipeline.script = _SCRIPT
    pipeline.run_dir = str(tmp_path)
    pipeline._synthesize_narration = fake_narration

    ok = await pipeline.run()

    assert ok is True
    assert len(gradient_calls) == 1
    assert gradient_calls[0][1] == 1080
    bg = [o for o in _FakeTimeline.instances[-1].overlays if "background_fallback" in o[0].uri]
    assert len(bg) == 1
    assert (bg[0][1]["start"], bg[0][1]["end"]) == (0.0, 150 / 30.0)


@pytest.mark.asyncio
async def test_hook_lead_in_prepends_silence_and_shifts_words(tmp_path, monkeypatch):
    async def fake_narration(lines):
        return list(_LINE_DATA)

    async def fake_segments(segments, fps):
        return [("/tmp/bg.mp4", 0, 150)]

    async def fake_group_by_thought(line, words, llm):
        return [words]

    def fake_hook_group(words, target_size=1):
        return [words]

    async def recorder(stage, progress, message):
        pass

    lead_calls = []

    def fake_prepend(wav, seconds, out_path, owner=""):
        lead_calls.append((wav, seconds, out_path, owner))
        with open(out_path, "wb") as fh:
            fh.write(b"padded")

    import shorts_creator.pipeline.compose as compose_mod

    real_build = compose_mod.build_compose_plan

    def fake_build(script, line_data, *args, **kwargs):
        captured["line_data"] = line_data
        return real_build(script, line_data, *args, **kwargs)

    captured = {}

    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_by_thought", fake_group_by_thought
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.captions.group_for_hook_display", fake_hook_group
    )
    monkeypatch.setattr("shorts_creator.pipeline.pipeline._render_hook_clip", lambda *a, **k: None)
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline._render_caption_clip", lambda *a, **k: None
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
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.generate_outro_clip", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "shorts_creator.pipeline.pipeline.stock_video._probe_duration", lambda *a, **k: 3.0
    )
    monkeypatch.setattr("lexigram.multimedia.timeline.Timeline", _FakeTimeline)
    monkeypatch.setattr("shorts_creator.pipeline.pipeline.narration.prepend_silence", fake_prepend)
    monkeypatch.setattr("shorts_creator.pipeline.compose.build_compose_plan", fake_build)
    _FakeTimeline.instances = []

    out_path = str(tmp_path / "out.mp4")
    pipeline = ReelPipeline(
        output=out_path,
        progress_callback=recorder,
        hook_lead_in_seconds=0.5,
    )
    pipeline.script = _SCRIPT
    pipeline.run_dir = str(tmp_path)
    pipeline._synthesize_narration = fake_narration
    pipeline._fetch_background_segments = fake_segments

    ok = await pipeline.run()

    assert ok is True
    assert len(lead_calls) == 1
    assert lead_calls[0][0] == "line_0.wav"
    assert lead_calls[0][1] == 0.5
    assert lead_calls[0][2].endswith("line_0_padded.wav")
    padded, duration, words = captured["line_data"][0]
    assert padded.endswith("line_0_padded.wav")
    assert duration == pytest.approx(3.5)
    assert words == [{"word": "A", "start": 0.5, "end": 3.5}]
    assert captured["line_data"][1] == (
        "line_1.wav",
        2.0,
        [{"word": "B", "start": 0.0, "end": 2.0}],
    )
    # hook frames grow by lead * fps: 105 instead of 90
    assert pipeline.duration_frames == 105 + 60 + 90


@pytest.mark.asyncio
async def test_progress_bridge_forwards_sync_percent_to_async_callback():
    captured = []

    async def recorder(stage, progress, message):
        captured.append((stage, progress))

    pipeline = ReelPipeline(progress_callback=recorder)
    pipeline._progress_tasks = set()
    bridge = pipeline._make_progress_bridge(asyncio.get_running_loop())

    bridge(0.0)
    bridge(0.5)
    bridge(1.0)
    if pipeline._progress_tasks:
        await asyncio.gather(*pipeline._progress_tasks)

    assert [p for s, p in captured if s == "render"] == [0.0, 0.5, 1.0]
