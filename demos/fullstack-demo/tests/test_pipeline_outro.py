"""Outro text fits within the canvas: shrink-to-fit then word-wrap,
so long outro copy never overflows the reel width (audit C4)."""

from PIL import Image, ImageDraw

from shorts_creator.pipeline import pipeline as pmod

CANVAS = pmod.REEL_WIDTH


def _text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


class TestFitOutroText:
    def test_short_text_stays_single_line_at_max_size(self):
        font, lines = pmod._fit_outro_text("Thanks!", CANVAS)
        assert lines == ["Thanks!"]
        assert font.size == 96

    def test_long_text_wraps_and_each_line_fits(self):
        text = (
            "This is a very long thank-you message that keeps going well past "
            "the width of the reel canvas at the maximum font size and then "
            "some more words to force wrapping."
        )
        font, lines = pmod._fit_outro_text(text, CANVAS)
        assert len(lines) > 1
        assert font.size == 24
        draw = ImageDraw.Draw(Image.new("RGBA", (CANVAS, 16)))
        for line in lines:
            assert _text_width(draw, line, font) <= int(CANVAS * 0.85)

    def test_medium_text_shrinks_to_fit_before_wrapping(self):
        text = "Thank you for watching this episode about deep focus"
        font, lines = pmod._fit_outro_text(text, CANVAS)
        assert lines == [text]
        assert 24 <= font.size < 96

    def test_no_wrap_when_single_word_still_too_wide(self):
        word = "C" * 200
        font, lines = pmod._fit_outro_text(word, CANVAS)
        assert len(lines) == 1
        assert font.size == 24


class TestRenderOutroTextClipUsesFit:
    def test_clip_builder_consumes_fit_result(self, tmp_path, monkeypatch):
        calls = {}

        def fake_fit(text, canvas_width, **kwargs):
            calls["text"] = text
            calls["width"] = canvas_width
            from PIL import ImageFont

            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24), [
                "line one",
                "line two",
            ]

        monkeypatch.setattr(pmod, "_fit_outro_text", fake_fit)
        monkeypatch.setattr(pmod.subprocess, "run", lambda *a, **k: None)

        out = str(tmp_path / "outro_text.mov")
        pmod._render_outro_text_clip("Some long outro text that should wrap", out, 3.0, 30.0)

        assert calls["text"] == "Some long outro text that should wrap"
        assert calls["width"] == CANVAS
