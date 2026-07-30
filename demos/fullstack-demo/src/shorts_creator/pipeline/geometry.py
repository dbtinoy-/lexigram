"""Daily Success Mindset — Short-form Reel Pipeline.

Orchestrates end-to-end reel creation: LLM script generation, TTS narration,
stock video sourcing, caption rendering, and ffmpeg compose render.
"""

import textwrap

from PIL import ImageFont

from shorts_creator.pipeline.constants import REEL_WIDTH

_AVG_CHAR_WIDTH_BOLD = 0.62
_AVG_CHAR_WIDTH_REGULAR = 0.60
_WIDTH_SAFETY_MARGIN = 1.15
_CAPTION_FONT_BOLD = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    48,
)
_HIGHLIGHT_PAD_PX = 8


def _text_width_px(text: str) -> float:
    return _CAPTION_FONT_BOLD.getlength(text)


def _avg_char_width_px(font_size: int, weight: int) -> float:
    return font_size * (_AVG_CHAR_WIDTH_BOLD if weight >= 700 else _AVG_CHAR_WIDTH_REGULAR)


def _wrap_lines(text: str, font_size: int, weight: int, max_width_px: float) -> list[str]:
    chars_per_line = max(1, int(max_width_px / _avg_char_width_px(font_size, weight)))
    return textwrap.wrap(text, width=chars_per_line, break_long_words=False) or [text]


_font_cache: dict[tuple[str | None, int], ImageFont.FreeTypeFont] = {}
_DEJAVU_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _bold_font(size: int, path: str | None = None) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path or _DEJAVU_BOLD, size)
    return _font_cache[key]


def _rgba_from_hex_colour(colour: str) -> tuple[int, int, int, int]:
    """Parse a '0xRRGGBBAA' colour into a PIL RGBA tuple."""
    h = colour.removeprefix("0x")
    return (
        int(h[0:2], 16),
        int(h[2:4], 16),
        int(h[4:6], 16),
        int(h[6:8], 16),
    )


def _word_key(text: str) -> str:
    """Lowercased alphanumerics only, so emphasis matching drops punctuation
    ("myth!" in the emphasis list still accents an on-screen "myth.")."""
    return "".join(ch for ch in text.lower() if ch.isalnum())


def _draw_pill(draw, cx: float, cy: float, text: str, font, fg_rgba, bg_rgba, pad: int) -> None:
    """Draw `text` centered at (cx, cy) with a background pill sized to the
    text's own bounding box plus padding - the background only sits behind
    rendered glyphs rather than across a fixed geometry box.
    """
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = right - left, bottom - top
    pill = (
        cx - text_w / 2 - pad,
        cy - text_h / 2 - pad,
        cx + text_w / 2 + pad,
        cy + text_h / 2 + pad,
    )
    draw.rounded_rectangle(pill, radius=pad, fill=bg_rgba)
    draw.text((cx - text_w / 2 - left, cy - text_h / 2 - top), text, font=font, fill=fg_rgba)


def _fit_caption_font_size(
    words: list[str], font_size: int, path: str | None = None, width: int = REEL_WIDTH
) -> int:
    """Shrink `font_size` down, if needed, so the whole chunk fits on one
    line within the caption region's width. Computed once per chunk (not
    per frame) so every frame in a chunk's highlight sequence uses the same
    size - text must not jitter between frames as the highlighted word changes.
    """
    region_width_px = width * 0.80
    size = font_size
    text = " ".join(words)
    while size > 24 and _bold_font(size, path).getlength(text) > region_width_px - 32:
        size -= 2
    return size
