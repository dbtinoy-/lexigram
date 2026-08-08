from shorts_creator.pipeline import captions
from shorts_creator.pipeline import pipeline as pmod
from shorts_creator.pipeline.pipeline import (
    CAPTION_HIGHLIGHT_COLOUR,
    _render_caption_frame,
    _render_list_frame,
)
from shorts_creator.pipeline.render_config import RenderConfig
from shorts_creator.pipeline.script_parser import apply_profile_overrides, to_pipeline_script


def _highlight_rgba():
    raw = CAPTION_HIGHLIGHT_COLOUR  # "0xRRGGBBAA"
    r = int(raw[2:4], 16)
    g = int(raw[4:6], 16)
    b = int(raw[6:8], 16)
    a = int(raw[8:10], 16)
    return (r, g, b, a)


class TestRenderCaptionFrame:
    def test_plain_style_draws_no_pill(self):
        img = _render_caption_frame(["one", "two"], highlighted_idx=None, font_size=64)
        assert img.mode == "RGBA"
        assert img.width == 1080
        assert img.height == 1920
        assert _highlight_rgba() not in set(img.get_flattened_data())

    def test_highlight_style_draws_pill(self):
        img = _render_caption_frame(["one", "two"], highlighted_idx=0, font_size=64)
        assert _highlight_rgba() in set(img.get_flattened_data())

    def test_highlight_style_moves_pill_per_word(self):
        img = _render_caption_frame(["one", "two"], highlighted_idx=1, font_size=64)
        assert _highlight_rgba() in set(img.get_flattened_data())

    def test_uppercase_knob_uppercases_words_before_layout(self, monkeypatch):
        texts = []
        real_text = pmod.ImageDraw.ImageDraw.text
        monkeypatch.setattr(
            pmod.ImageDraw.ImageDraw,
            "text",
            lambda self, xy, text, *a, **k: (
                texts.append(text),
                real_text(self, xy, text, *a, **k),
            )[1],
        )
        _render_caption_frame(
            ["one", "two"],
            highlighted_idx=None,
            font_size=64,
            render_config=RenderConfig(caption_uppercase=True),
        )
        assert texts == ["ONE", "TWO"]

    def test_scrim_drawn_behind_line_when_alpha_set(self, monkeypatch):
        rects = []
        real_rr = pmod.ImageDraw.ImageDraw.rounded_rectangle
        monkeypatch.setattr(
            pmod.ImageDraw.ImageDraw,
            "rounded_rectangle",
            lambda self, xy, *a, **k: (rects.append(xy), real_rr(self, xy, *a, **k))[1],
        )
        _render_caption_frame(
            ["one", "two"],
            highlighted_idx=None,
            font_size=64,
            render_config=RenderConfig(caption_scrim_alpha=0.5),
        )
        assert len(rects) == 1
        left, top, right, bottom = rects[0]
        assert left <= 108 and right >= 972
        assert top <= 960 and bottom >= 960

    def test_no_scrim_when_alpha_zero(self, monkeypatch):
        rects = []
        real_rr = pmod.ImageDraw.ImageDraw.rounded_rectangle
        monkeypatch.setattr(
            pmod.ImageDraw.ImageDraw,
            "rounded_rectangle",
            lambda self, xy, *a, **k: (rects.append(xy), real_rr(self, xy, *a, **k))[1],
        )
        _render_caption_frame(["one"], highlighted_idx=None, font_size=64)
        assert rects == []


def _content_bbox(img):
    w, h = img.width, img.height
    data = img.get_flattened_data()
    min_x, min_y, max_x, max_y = w, h, -1, -1
    for i, px in enumerate(data):
        if px[3] > 0:
            x, y = i % w, i // w
            min_x, max_x = min(min_x, x), max(max_x, x)
            min_y, max_y = min(min_y, y), max(max_y, y)
    return (min_x, min_y, max_x, max_y)


class TestEmphasisWords:
    def test_default_emphasis_style_is_accent(self):
        assert RenderConfig().emphasis_style == "accent"

    def test_empty_emphasize_keeps_baseline_pixels(self):
        base = _render_caption_frame(["myth"], highlighted_idx=None, font_size=64)
        empty = _render_caption_frame(["myth"], highlighted_idx=None, font_size=64, emphasize=set())
        assert list(empty.get_flattened_data()) == list(base.get_flattened_data())
        assert _highlight_rgba() not in set(base.get_flattened_data())

    def test_accent_style_colours_emphasized_word(self):
        img = _render_caption_frame(
            ["myth"], highlighted_idx=None, font_size=64, emphasize={"myth"}
        )
        assert _highlight_rgba() in set(img.get_flattened_data())

    def test_off_style_ignores_emphasize(self):
        base = _render_caption_frame(["myth"], highlighted_idx=None, font_size=64)
        off = _render_caption_frame(
            ["myth"],
            highlighted_idx=None,
            font_size=64,
            emphasize={"myth"},
            render_config=RenderConfig(emphasis_style="off"),
        )
        assert list(off.get_flattened_data()) == list(base.get_flattened_data())

    def test_scale_style_enlarges_emphasized_word(self):
        base = _render_caption_frame(["myth"], highlighted_idx=None, font_size=64)
        scaled = _render_caption_frame(
            ["myth"],
            highlighted_idx=None,
            font_size=64,
            emphasize={"myth"},
            render_config=RenderConfig(emphasis_style="scale"),
        )
        base_w = _content_bbox(base)[2] - _content_bbox(base)[0]
        scaled_w = _content_bbox(scaled)[2] - _content_bbox(scaled)[0]
        assert scaled_w > base_w

    def test_emphasize_matching_is_case_insensitive(self):
        low = _render_caption_frame(
            ["myth"], highlighted_idx=None, font_size=64, emphasize={"myth"}
        )
        up = _render_caption_frame(["myth"], highlighted_idx=None, font_size=64, emphasize={"MYTH"})
        assert list(low.get_flattened_data()) == list(up.get_flattened_data())

    def test_emphasize_matching_ignores_punctuation(self):
        word_punct = _render_caption_frame(
            ["myth."], highlighted_idx=None, font_size=64, emphasize={"myth"}
        )
        token_punct = _render_caption_frame(
            ["myth"], highlighted_idx=None, font_size=64, emphasize={"myth!"}
        )
        plain = _render_caption_frame(["myth"], highlighted_idx=None, font_size=64)
        assert _highlight_rgba() in set(word_punct.get_flattened_data())
        assert _highlight_rgba() in set(token_punct.get_flattened_data())
        assert _highlight_rgba() not in set(plain.get_flattened_data())


class TestRenderCaptionFramePixels:
    def _words(self):
        return [{"word": "not"}, {"word": "a"}, {"word": "myth"}]

    def test_emphasis_words_render_accented(self):
        words = self._words()
        chars = captions.render_caption_frame_pixels(words, highlighted_idx=1, emphasize={"myth"})
        base = captions.render_caption_frame_pixels(words, highlighted_idx=1, emphasize=set())
        assert chars != base

    def test_off_style_keeps_baseline_bytes(self):
        words = self._words()
        base = captions.render_caption_frame_pixels(words, highlighted_idx=1, emphasize=set())
        off = captions.render_caption_frame_pixels(
            words,
            highlighted_idx=1,
            emphasize={"myth"},
            render_config=RenderConfig(emphasis_style="off"),
        )
        assert off == base


class TestEmphasisWordsFolding:
    def _saved(self, **extra):
        saved = {
            "title": "T",
            "sections": [
                {"name": "hook", "text": "H", "duration_seconds": 4.0},
                {"name": "message", "text": "M", "duration_seconds": 6.0},
            ],
        }
        saved.update(extra)
        return saved

    def test_to_pipeline_script_reads_emphasis_list(self):
        s = to_pipeline_script(self._saved(emphasis=["fact", "myth"]))
        assert s.emphasis == ["fact", "myth"]

    def test_to_pipeline_script_splits_string_emphasis(self):
        s = to_pipeline_script(self._saved(emphasis="fact, myth\n twist"))
        assert s.emphasis == ["fact", "myth", "twist"]

    def test_to_pipeline_script_ignores_blank_emphasis(self):
        assert to_pipeline_script(self._saved(emphasis=[])).emphasis == []

    def test_apply_profile_overrides_parses_emphasis_words(self):
        s = apply_profile_overrides(self._saved(), {"emphasis_words": "fact, myth\n twist"})
        assert s.emphasis == ["fact", "myth", "twist"]

    def test_apply_profile_overrides_keeps_saved_emphasis_without_snapshot(self):
        s = apply_profile_overrides(self._saved(emphasis=["fact"]), {})
        assert s.emphasis == ["fact"]


class TestRenderListFrame:
    def test_draws_two_pills_per_item_left_to_right(self, monkeypatch):
        rects = []
        real_rr = pmod.ImageDraw.ImageDraw.rounded_rectangle
        monkeypatch.setattr(
            pmod.ImageDraw.ImageDraw,
            "rounded_rectangle",
            lambda self, xy, *a, **k: (rects.append(xy), real_rr(self, xy, *a, **k))[1],
        )
        _render_list_frame([("1", "One"), ("2", "Two")], font_size=64)
        assert len(rects) == 4  # number pill + text pill per item
        for i in range(0, len(rects), 2):
            assert rects[i][2] < rects[i + 1][0]

    def test_rows_stacked_and_vertically_centered(self, monkeypatch):
        rects = []
        real_rr = pmod.ImageDraw.ImageDraw.rounded_rectangle
        monkeypatch.setattr(
            pmod.ImageDraw.ImageDraw,
            "rounded_rectangle",
            lambda self, xy, *a, **k: (rects.append(xy), real_rr(self, xy, *a, **k))[1],
        )
        _render_list_frame([("1", "One"), ("2", "Two")], font_size=64)
        centers = sorted({round((r[1] + r[3]) / 2) for r in rects})
        assert centers == [909, 1011]  # 83.2px rows + 18px gap, centered on 960
