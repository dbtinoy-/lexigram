"""Configured reel dimensions flow through the render canvas + assets.

Changing `app.reel_width` / `app.reel_height` (application.yaml) must resize
every baked overlay (hook, captions, watermark, gradient/outro), the
background fit, and the final encode - verified here on the pure
PIL/compose paths that don't shell out to ffmpeg.
"""

from typing import ClassVar

from shorts_creator.pipeline.compose import build_compose_plan, hook_font_size
from shorts_creator.pipeline.pipeline import (
    REEL_HEIGHT,
    REEL_WIDTH,
    ReelPipeline,
    _centered_row_geometry,
    _fit_caption_font_size,
    _render_caption_frame,
    _render_checked_frame,
    _render_hook_frame,
    _render_ranked_frame,
)
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


class TestReelPipelineDimensions:
    def test_defaults_match_reel_constants(self):
        pipeline = ReelPipeline()
        assert (pipeline.reel_width, pipeline.reel_height) == (REEL_WIDTH, REEL_HEIGHT)

    def test_custom_dimensions_stored(self):
        pipeline = ReelPipeline(reel_width=720, reel_height=1280)
        assert (pipeline.reel_width, pipeline.reel_height) == (720, 1280)

    def test_non_positive_dimensions_rejected(self):
        try:
            ReelPipeline(reel_width=0, reel_height=1280)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for non-positive reel width")


class TestRenderFramesFollowDimensions:
    def test_caption_frame_default_canvas_is_reel(self):
        img = _render_caption_frame(["one", "two"], highlighted_idx=0, font_size=64)
        assert img.size == (REEL_WIDTH, REEL_HEIGHT)

    def test_caption_frame_follows_configured_dimensions(self):
        img = _render_caption_frame(
            ["one", "two"], highlighted_idx=0, font_size=64, width=360, height=640
        )
        assert img.size == (360, 640)

    def test_hook_frame_follows_configured_dimensions(self):
        img = _render_hook_frame(["Wake up", "and go"], 42, width=540, height=960)
        assert img.size == (540, 960)

    def test_ranked_frame_follows_configured_dimensions(self):
        img = _render_ranked_frame("1", ["Wake", "up"], 42, width=540, height=960)
        assert img.size == (540, 960)

    def test_ranked_frame_number_renders_larger_than_pills(self):
        img = _render_ranked_frame("1", ["Wake", "up"], 42, width=540, height=960)
        alpha = img.getchannel("A")
        rows = [y for y in range(960) if any(alpha.getpixel((x, y)) for x in range(0, 540, 7))]
        assert len(rows) > 0  # three stacked rows (number + two pills)
        span = max(rows) - min(rows)
        assert span > 100

    def test_checked_frame_follows_configured_dimensions(self):
        img = _render_checked_frame("1", ["Wake", "up"], 42, width=540, height=960)
        assert img.size == (540, 960)

    def test_checked_frame_number_renders_larger_than_pills(self):
        img = _render_checked_frame("1", ["Wake", "up"], 42, width=540, height=960)
        alpha = img.getchannel("A")
        rows = [y for y in range(960) if any(alpha.getpixel((x, y)) for x in range(0, 540, 7))]
        assert len(rows) > 0  # number row + check-marked pills
        span = max(rows) - min(rows)
        assert span > 100

    def test_checked_frame_check_pills_use_highlight_colour(self):
        from shorts_creator.pipeline.pipeline import _rgba_from_hex_colour

        highlight = _rgba_from_hex_colour("0x7C5CFAFF")
        img = _render_checked_frame("1", ["Wake", "up"], 42, width=540, height=960)
        pixels = list(img.get_flattened_data())
        assert pixels.count(highlight) > 200  # check pills in the highlight colour
        assert pixels.count((255, 255, 255, 255)) > 200  # number + check-mark glyphs

        ranked = _render_ranked_frame("1", ["Wake", "up"], 42, width=540, height=960)
        assert list(ranked.get_flattened_data()).count(highlight) == 0

    def test_caption_font_shrinks_on_narrower_canvas(self):
        words = ["responsibility", "obligation", "accountability"]
        wide = _fit_caption_font_size(words, 64, width=REEL_WIDTH)
        narrow = _fit_caption_font_size(words, 64, width=400)
        assert 0 < narrow < wide

    def test_centered_row_geometry_uses_configured_canvas_height(self):
        top_pct, _ = _centered_row_geometry(48, 0, 2, gap_px=18, height=800)
        assert 0.0 <= top_pct <= 100.0
        assert top_pct > 0  # 48px block + gap must leave margin on a short 800px canvas


class TestComposePlanFollowsDimensions:
    _line_data: ClassVar[list[tuple[str, float, list[dict]]]] = [
        ("/tmp/l0.wav", 2.0, [{"word": "Hello", "start": 0.0, "end": 2.0}]),
        ("/tmp/l1.wav", 2.0, [{"word": "World", "start": 0.0, "end": 2.0}]),
        ("/tmp/l2.wav", 2.0, [{"word": "Again", "start": 0.0, "end": 2.0}]),
    ]

    def _plan(self, width, height):
        return build_compose_plan(
            _SCRIPT,
            self._line_data,
            bg_path="/tmp/bg.mp4",
            fps=30.0,
            width=width,
            height=height,
        )

    def test_encode_resolution_follows_configured_dimensions(self):
        plan = self._plan(720, 1280)
        assert plan.encode.resolution == "720x1280"

    def test_encode_resolution_defaults_to_reel(self):
        plan = build_compose_plan(_SCRIPT, self._line_data, bg_path="/tmp/bg.mp4", fps=30.0)
        assert plan.encode.resolution == f"{REEL_WIDTH}x{REEL_HEIGHT}"

    def test_hook_font_size_follows_configured_dimensions(self):
        texts = ["Wake up", "and grind"]
        wide = hook_font_size(texts, width=REEL_WIDTH, height=REEL_HEIGHT)
        narrow = hook_font_size(texts, width=360, height=640)
        assert narrow <= wide


def test_ranked_frame_scale_follows_render_config():
    from shorts_creator.pipeline.render_config import RenderConfig

    img1 = _render_ranked_frame("1", ["Wake", "up"], 42, width=540, height=960)
    img2 = _render_ranked_frame(
        "1",
        ["Wake", "up"],
        42,
        width=540,
        height=960,
        render_config=RenderConfig(ranked_number_scale=0.8),
    )
    alpha1 = img1.getchannel("A")
    alpha2 = img2.getchannel("A")
    rows1 = [y for y in range(960) if any(alpha1.getpixel((x, y)) for x in range(0, 540, 7))]
    rows2 = [y for y in range(960) if any(alpha2.getpixel((x, y)) for x in range(0, 540, 7))]
    assert max(rows1) - min(rows1) > max(rows2) - min(rows2)


def test_lower_third_anchor_moves_hook_block_down():
    from shorts_creator.pipeline.render_config import RenderConfig

    img = _render_hook_frame(
        ["Wake up", "and go"],
        42,
        width=540,
        height=960,
        render_config=RenderConfig(anchor="lower_third"),
    )
    alpha = img.getchannel("A")
    rows = [y for y in range(960) if any(alpha.getpixel((x, y)) for x in range(0, 540, 7))]
    assert min(rows) > 100  # block starts well below the vertical center
