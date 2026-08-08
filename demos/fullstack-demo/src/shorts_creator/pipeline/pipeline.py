"""Daily Success Mindset — Short-form Reel Pipeline.

Orchestrates end-to-end reel creation: LLM script generation, TTS narration,
stock video sourcing, caption rendering, and ffmpeg compose render.
"""

import asyncio
import functools
import os
import shutil
import subprocess
import tempfile
import textwrap
import time
from collections.abc import Callable
from typing import TextIO

from PIL import Image, ImageDraw, ImageFont

from shorts_creator.pipeline.render_config import RenderConfig
from shorts_creator.pipeline.script_parser import ParsedScript
from shorts_creator.services.asset_service import ASSETS_ROOT
from shorts_creator.topics.base import Idea

REEL_WIDTH = 1080
REEL_HEIGHT = 1920

SAMPLE_BACKGROUND = ASSETS_ROOT / "clip" / "sample_nature_asmr.mp4"

_PIPELINE_START = time.time()

_LOG_TEES: dict[int, TextIO] = {}


def add_log_tee(stream: TextIO) -> None:
    """Register an extra write target for pipeline stage traces.

    Unlike a global ``redirect_stdout``, this only tees the pipeline's own
    ``_log`` output. Concurrent renders each register their own stream, so
    sys.stdout is never swapped process-wide and other requests keep logging
    normally.
    """
    _LOG_TEES[id(stream)] = stream


def remove_log_tee(stream: TextIO) -> None:
    _LOG_TEES.pop(id(stream), None)


def _log(msg: str) -> None:
    """Print with an elapsed-since-start prefix so a live-tailed log shows
    exactly when each stage ran and how long gaps between them were -
    needed to tell "still working" apart from "stuck" during a run.
    """
    line = f"[{time.time() - _PIPELINE_START:7.1f}s] {msg}"
    print(line)
    for stream in list(_LOG_TEES.values()):
        try:
            stream.write(line + "\n")
        except (ValueError, OSError):  # tee closed mid-run; logging is best-effort
            pass


# Average glyph width as a fraction of font size for DejaVu Sans. Headless
# rendering has no font-metrics API, so line wrapping/width is estimated from
# character count rather than measured - close enough to size CapCut-style
# per-line background pills without a giant fixed box around sparse text.
# Skewed high on purpose: an undershoot makes qtext internally re-wrap the
# line, which then gets clipped by the (single-line-height) geometry box and
# silently drops text - an overshoot just leaves a little extra pill padding.
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


def _render_caption_frame(
    words: list[str],
    highlighted_idx: int | None,
    font_size: int,
    path: str | None = None,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    render_config: RenderConfig | None = None,
    highlight_colour: str | None = None,
    emphasize: set[str] | None = None,
) -> "Image.Image":
    """One static frame of a body-caption chunk: every word in `words` stays
    visible, but only `words[highlighted_idx]` gets the highlight pill
    pill behind it - baking the highlight into pixels via ffmpeg (see
    _render_caption_clip) keeps one clip per chunk while bringing per-word
    tracking back. When `highlighted_idx` is None (plain style) no pill is
    drawn and the whole line reads as static text. Words in `emphasize`
    (matched case-insensitively, ignoring punctuation) are drawn in the
    accent colour when cfg.emphasis_style is "accent" or enlarged 1.25x
    when "scale". An empty/omitted `emphasize` renders byte-identical to
    the pre-emphasis path.
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _bold_font(font_size, path)
    cfg = render_config or RenderConfig()
    if cfg.caption_uppercase:
        words = [word.upper() for word in words]

    top_pct, height_pct = _centered_row_geometry(font_size, 0, 1, height=height)
    y_center_px = (top_pct + height_pct / 2) / 100 * height

    region_left_px = width * 0.10
    region_width_px = width * 0.80
    space_w = draw.textlength(" ", font=font)
    word_widths = [draw.textlength(w, font=font) for w in words]
    total_w = sum(word_widths) + space_w * (len(words) - 1)
    cursor_x = region_left_px + max(0.0, (region_width_px - total_w) / 2)

    if cfg.caption_scrim_alpha > 0:
        ascent, descent = font.getmetrics()
        line_half_h = (ascent + descent) / 2 + _HIGHLIGHT_PAD_PX
        scrim = (
            region_left_px,
            y_center_px - line_half_h,
            region_left_px + region_width_px,
            y_center_px + line_half_h,
        )
        scrim_rgba = (0, 0, 0, round(255 * cfg.caption_scrim_alpha))
        draw.rounded_rectangle(scrim, radius=_HIGHLIGHT_PAD_PX, fill=scrim_rgba)

    highlight_bg = _rgba_from_hex_colour(
        highlight_colour if highlight_colour is not None else cfg.caption_highlight_colour
    )
    pad = _HIGHLIGHT_PAD_PX
    ascent, descent = font.getmetrics()
    half_h = (ascent + descent) / 2

    emphasize_keys = {_word_key(w) for w in emphasize or ()}
    for i, word in enumerate(words):
        word_w = word_widths[i]
        emphasized = _word_key(word) in emphasize_keys
        word_font = font
        fill = (255, 255, 255, 255)
        if emphasized and cfg.emphasis_style == "scale":
            word_font = _bold_font(round(font_size * 1.25), path)
            word_w = draw.textlength(word, font=word_font)
        elif emphasized and cfg.emphasis_style == "accent":
            fill = highlight_bg
        if highlighted_idx is not None and i == highlighted_idx:
            pill = (
                cursor_x - pad,
                y_center_px - half_h - pad,
                cursor_x + word_w + pad,
                y_center_px + half_h + pad,
            )
            draw.rounded_rectangle(pill, radius=pad, fill=highlight_bg)
        draw.text(
            (cursor_x, y_center_px),
            word,
            font=word_font,
            fill=fill,
            anchor="lm",
            stroke_width=cfg.caption_outline_width,
            stroke_fill=(0, 0, 0, 255),
        )
        cursor_x += word_w + space_w

    return img


def _render_caption_clip(
    words: list[str],
    word_frames: list[int],
    fps: float,
    font_size: int,
    out_path: str,
    trim_tail: bool = False,
    style: str = "highlight",
    path: str | None = None,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    render_config: RenderConfig | None = None,
    highlight_colour: str | None = None,
    emphasize: set[str] | None = None,
) -> None:
    """Render one body-caption chunk as a transparent .mov: one frame per
    word in `words`, each held for its matching `word_frames[i]` duration,
    with only that word's highlight pill visible - see _render_caption_frame.

    Args:
        trim_tail: When True (ffmpeg compose path), cut the output to exactly
            the sum of the word holds so the last word's highlight never
            lingers past its spoken end once the clip's frames run out.
        style: "highlight" tracks each word with a moving pill; "plain"
            renders the whole chunk statically (no pill) for the same
            per-word timing so the line reads as fixed text.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_paths, durations = [], []
        for i in range(len(words)):
            frame_path = os.path.join(tmp_dir, f"w{i}.png")
            highlighted = i if style == "highlight" else None
            _render_caption_frame(
                words,
                highlighted_idx=highlighted,
                font_size=font_size,
                path=path,
                width=width,
                height=height,
                render_config=render_config,
                highlight_colour=highlight_colour,
                emphasize=emphasize,
            ).save(frame_path)
            frame_paths.append(frame_path)
            durations.append(word_frames[i] / fps)

        if trim_tail:
            # Exact-trim path: the concat demuxer drops or shortens the
            # final entry's hold, so stitch the frames with the concat
            # filter instead - each looped PNG input is held for exactly
            # its word duration and the output ends when the last word
            # stops being spoken. The last input gets a one-frame pad so a
            # duration rounding down never shortens the final hold; the
            # compose window clips any overshoot.
            inputs, chains = [], []
            for i, (frame_path, duration) in enumerate(zip(frame_paths, durations)):
                pad = (1 / fps + 0.001) if i == len(durations) - 1 else 0.0
                inputs += [
                    "-loop",
                    "1",
                    "-framerate",
                    str(fps),
                    "-t",
                    f"{duration + pad:.4f}",
                    "-i",
                    frame_path,
                ]
                chains.append(f"[{i}:v]")
            cmd = [
                "ffmpeg",
                "-y",
                *inputs,
                "-filter_complex",
                f"{''.join(chains)}concat=n={len(chains)}:v=1:a=0[v]",
                "-map",
                "[v]",
                "-pix_fmt",
                "argb",
                "-c:v",
                "qtrle",
                "-r",
                str(fps),
                out_path,
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            return

        list_path = os.path.join(tmp_dir, "concat.txt")
        with open(list_path, "w") as f:
            for i, (frame_path, duration) in enumerate(zip(frame_paths, durations)):
                # Only the final word's frame gets a safety margin, so the
                # later resize_clip trim never runs out of encoded source
                # frames to cut from - padding every frame would push every
                # subsequent word's on-screen transition later than the word
                # actually spoken, drifting the highlight out of sync with the
                # narration.
                margin = 0.5 if i == len(durations) - 1 else 0.0
                f.write(f"file '{frame_path}'\nduration {duration + margin:.3f}\n")
            f.write(f"file '{frame_paths[-1]}'\n")

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            list_path,
            "-pix_fmt",
            "argb",
            "-c:v",
            "qtrle",
            "-r",
            str(fps),
            out_path,
        ]
        subprocess.run(cmd, capture_output=True, check=True)


def _centered_row_geometry(
    font_size: float,
    line_idx: int,
    num_lines: int,
    gap_px: float = 0.0,
    height: int = REEL_HEIGHT,
    anchor: str = "center",
) -> tuple[float, float]:
    """Return (top_pct, height_pct) for one row of a `num_lines`-tall caption
    stack vertically centered in the frame, with `gap_px` of breathing room
    between rows. Shared by the hook's stacked block and regular highlight
    captions so every caption sits in the same centered region.
    """
    line_height_px = font_size * HOOK_LINE_HEIGHT_FACTOR
    block_height_px = line_height_px * num_lines + gap_px * (num_lines - 1)
    if anchor == "lower_third":
        block_top_px = height * 0.66 - block_height_px / 2
    else:
        block_top_px = (height - block_height_px) / 2
    top_px = block_top_px + line_idx * (line_height_px + gap_px)
    return round(top_px / height * 100, 2), round(line_height_px / height * 100, 2)


def _render_hook_frame(
    texts: list[str],
    hook_font_size: int,
    path: str | None = None,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    render_config: RenderConfig | None = None,
) -> "Image.Image":
    """One static frame for the Hook screen: each line in `texts` gets its
    own rounded-corner background pill, stacked and centered via the same
    _centered_row_geometry math the old dynamictext rows used.
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _bold_font(hook_font_size, path)
    cfg = render_config or RenderConfig()
    text_bg = _rgba_from_hex_colour(cfg.pill_bg_colour)
    for line_idx, text in enumerate(texts):
        top_pct, height_pct = _centered_row_geometry(
            hook_font_size,
            line_idx,
            len(texts),
            gap_px=cfg.hook_line_gap_px,
            height=height,
            anchor=cfg.anchor,
        )
        cy_px = (top_pct + height_pct / 2) / 100 * height
        _draw_pill(
            draw,
            width / 2,
            cy_px,
            text,
            font,
            (255, 255, 255, 255),
            text_bg,
            pad=12,
        )
    return img


RANKED_NUMBER_SCALE = 1.6  # item number glyph size as a multiple of the pill font


def _render_ranked_frame(
    number: str,
    texts: list[str],
    font_size: int,
    path: str | None = None,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    render_config: RenderConfig | None = None,
) -> "Image.Image":
    """One static frame for a ranked item screen (topn): the item number as
    a large pill over the item text as hook-style word pills, all centered.
    The number row is taller than the pill rows, so the caller must size the
    pill font over `[number] + texts` lines (hook_font_size) for the screen
    to fit and for the preview font math to match exactly."""
    cfg = render_config or RenderConfig()
    num_font = round(font_size * cfg.ranked_number_scale)
    num_rows = len(texts) + 1
    pill_row_h = font_size * cfg.hook_line_height_factor
    num_row_h = num_font * cfg.hook_line_height_factor
    block_h = num_row_h + pill_row_h * len(texts) + cfg.hook_line_gap_px * (num_rows - 1)
    if cfg.anchor == "lower_third":
        top_px = height * 0.66 - block_h / 2
    else:
        top_px = (height - block_h) / 2

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    text_bg = _rgba_from_hex_colour(cfg.pill_bg_colour)
    num_font_obj = _bold_font(num_font, path)
    pill_font = _bold_font(font_size, path)

    _draw_pill(
        draw,
        width / 2,
        top_px + num_row_h / 2,
        number,
        num_font_obj,
        (255, 255, 255, 255),
        text_bg,
        pad=12,
    )
    for idx, text in enumerate(texts):
        cy_px = top_px + num_row_h + idx * (pill_row_h + cfg.hook_line_gap_px) + pill_row_h / 2
        _draw_pill(
            draw,
            width / 2,
            cy_px,
            text,
            pill_font,
            (255, 255, 255, 255),
            text_bg,
            pad=12,
        )
    return img


def _render_ranked_clip(
    number: str,
    texts: list[str],
    font_size: int,
    fps: float,
    display_frames: int,
    out_path: str,
    path: str | None = None,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    render_config: RenderConfig | None = None,
) -> None:
    """Bake one ranked item screen (big number + hook-style word pills) as a
    transparent .mov clip, same static-frame encoding as the hook screen."""
    _bake_static_clip(
        _render_ranked_frame(
            number,
            texts,
            font_size,
            path=path,
            width=width,
            height=height,
            render_config=render_config,
        ),
        fps,
        display_frames,
        out_path,
    )


def _render_checked_frame(
    number: str,
    texts: list[str],
    font_size: int,
    path: str | None = None,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    render_config: RenderConfig | None = None,
) -> "Image.Image":
    """One static frame for a checklist screen (steps): the step number as a
    large pill over each step line prefixed with a check mark, all centered.
    Mirrors _render_ranked_frame's geometry: the number row is taller than
    the pill rows, so the caller must size the pill font over
    `[number] + texts` lines (hook_font_size) for the screen to fit."""
    cfg = render_config or RenderConfig()
    rows = texts if texts else [""]
    num_font = round(font_size * cfg.ranked_number_scale)
    pill_row_h = font_size * cfg.hook_line_height_factor
    num_row_h = num_font * cfg.hook_line_height_factor
    gap = cfg.hook_line_gap_px
    block_h = num_row_h + pill_row_h * len(rows) + gap * len(rows)
    if cfg.anchor == "lower_third":
        top_px = height * 0.66 - block_h / 2
    else:
        top_px = (height - block_h) / 2

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    number_bg = _rgba_from_hex_colour(cfg.pill_bg_colour)
    check_bg = _rgba_from_hex_colour(cfg.caption_highlight_colour)
    _draw_pill(
        draw,
        width / 2,
        top_px + num_row_h / 2,
        number,
        _bold_font(num_font, path),
        (255, 255, 255, 255),
        number_bg,
        pad=12,
    )
    pill_font = _bold_font(font_size, path)
    for idx, text in enumerate(rows):
        cy_px = top_px + num_row_h + idx * (pill_row_h + gap) + pill_row_h / 2
        _draw_pill(
            draw,
            width / 2,
            cy_px,
            f"\u2713 {text}",
            pill_font,
            (255, 255, 255, 255),
            check_bg,
            pad=12,
        )
    return img


def _render_checked_clip(
    number: str,
    texts: list[str],
    font_size: int,
    fps: float,
    display_frames: int,
    out_path: str,
    path: str | None = None,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    render_config: RenderConfig | None = None,
) -> None:
    """Bake one checklist screen (big number + check-marked lines) as a
    transparent .mov clip, same static-frame encoding as the ranked screen."""
    _bake_static_clip(
        _render_checked_frame(
            number,
            texts,
            font_size,
            path=path,
            width=width,
            height=height,
            render_config=render_config,
        ),
        fps,
        display_frames,
        out_path,
    )


def _rank_render_clip(rank_style: str):
    """Pick the ranked-screen renderer: checklist pills for "check", numbered
    pills otherwise (topn default)."""
    return _render_checked_clip if rank_style == "check" else _render_ranked_clip


def _render_list_frame(
    items: list[tuple[str, str]],
    font_size: int,
    path: str | None = None,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    render_config: RenderConfig | None = None,
) -> "Image.Image":
    """One static frame for the topn full-list screen ("list" caption
    style): every ranked item on its own row as a small number pill beside
    its text pill, all rows stacked and centered. The caller must size the
    font over the row texts (hook_font_size) so all rows fit the block."""
    cfg = render_config or RenderConfig()
    rows = items if items else [("1", "")]
    pill_row_h = font_size * cfg.hook_line_height_factor
    gap = cfg.hook_line_gap_px
    block_h = pill_row_h * len(rows) + gap * (len(rows) - 1)
    if cfg.anchor == "lower_third":
        top_px = height * 0.66 - block_h / 2
    else:
        top_px = (height - block_h) / 2

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _bold_font(font_size, path)
    bg = _rgba_from_hex_colour(cfg.pill_bg_colour)
    pad = 12
    for i, (number, text) in enumerate(rows):
        cy_px = top_px + i * (pill_row_h + gap) + pill_row_h / 2
        num_w = draw.textlength(number, font=font)
        text_w = draw.textlength(text, font=font)
        group_w = num_w + text_w + pad * 4
        _draw_pill(
            draw,
            width / 2 - group_w / 2 + num_w / 2,
            cy_px,
            number,
            font,
            (255, 255, 255, 255),
            bg,
            pad=pad,
        )
        _draw_pill(
            draw,
            width / 2 + group_w / 2 - text_w / 2,
            cy_px,
            text,
            font,
            (255, 255, 255, 255),
            bg,
            pad=pad,
        )
    return img


def _render_list_clip(
    items: list[tuple[str, str]],
    font_size: int,
    fps: float,
    display_frames: int,
    out_path: str,
    path: str | None = None,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    render_config: RenderConfig | None = None,
) -> None:
    """Bake one topn full-list screen as a transparent .mov clip, same
    static-frame encoding as the ranked screen."""
    _bake_static_clip(
        _render_list_frame(
            items, font_size, path=path, width=width, height=height, render_config=render_config
        ),
        fps,
        display_frames,
        out_path,
    )


def _render_hook_clip(
    texts: list[str],
    hook_font_size: int,
    fps: float,
    display_frames: int,
    out_path: str,
    path: str | None = None,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    render_config: RenderConfig | None = None,
) -> None:
    """Render the Hook screen as a single transparent .mov clip via PIL +
    ffmpeg, mirroring _render_caption_clip. MLT's
    dynamictext filter (the RPC path this replaced) has no rounded-corner
    background parameter - bgcolour+pad paint only a plain rectangle
    (confirmed against filter_dynamictext.yml) - so the rounded pill style
    already used for captions can only be produced by pre-rendering
    pixels instead.
    """
    _bake_static_clip(
        _render_hook_frame(
            texts,
            hook_font_size,
            path=path,
            width=width,
            height=height,
            render_config=render_config,
        ),
        fps,
        display_frames,
        out_path,
    )


def _bake_static_clip(frame: "Image.Image", fps: float, display_frames: int, out_path: str) -> None:
    """Encode a single static RGBA frame into a transparent .mov clip held
    for display_frames/fps seconds. Shared by the hook and ranked-item
    screens. The +0.5s safety margin is so the later resize_clip trim never
    runs out of encoded source frames to cut from - safe here since the
    whole screen is a single static frame, with no internal word-to-word
    timing that could drift out of sync.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_path = os.path.join(tmp_dir, "static.png")
        frame.save(frame_path)

        list_path = os.path.join(tmp_dir, "concat.txt")
        duration = display_frames / fps
        with open(list_path, "w") as f:
            f.write(f"file '{frame_path}'\nduration {duration + 0.5:.3f}\n")
            f.write(f"file '{frame_path}'\n")

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            list_path,
            "-pix_fmt",
            "argb",
            "-c:v",
            "qtrle",
            "-r",
            str(fps),
            out_path,
        ]
        subprocess.run(cmd, capture_output=True, check=True)


from lexigram.contracts.multimedia.types import MediaAsset

from . import captions, narration, prompts, stock_video
from .seo import research_content_angles

DEFAULT_DURATION_SECONDS = 30
RENDER_TIMEOUT = 600  # seconds - scripts now run 38-50s (up from 20-29s),
# so rendering takes longer than the old budget
CAPTION_FONT_SIZE = 56
HOOK_MIN_FONT_SIZE = 40
HOOK_MAX_FONT_SIZE = 110
HOOK_CHAR_WIDTH_FACTOR = 0.55  # avg glyph width as a fraction of font size, DejaVu Sans 800-weight
HOOK_LINE_HEIGHT_FACTOR = 1.3  # text height incl. leading, as a multiple of font size
HOOK_BLOCK_WIDTH_PCT = 80
HOOK_BLOCK_HEIGHT_PCT = (
    70  # soft ceiling - lines are sized for legibility first, never stretched to fill this
)
HOOK_LINE_GAP_PX = 18  # vertical breathing room between the hook's stacked text bars
CAPTION_HIGHLIGHT_COLOUR = "0x7C5CFAFF"  # current-word highlight box
CAPTION_MAX_WORDS = 3  # cap words shown at once for body captions
CAPTION_OUTLINE_WIDTH = 2  # px stroke around caption glyphs, since there's no bgcolour
# box behind the line anymore (bgcolour) - text needs its own contrast against footage
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUTRO_DEFAULT_PATH = os.path.join(_PROJECT_ROOT, "templates", "outro_default.mp4")
OUTRO_DEFAULT_SECONDS = 3.0  # duration baked into the generated default outro clip
FADE_IN_SECONDS = 0.5  # fade-in duration for the first clip
FADE_OUT_SECONDS = 1.0  # fade-out duration for the last clip


def held_line_frames(
    line_data: list[tuple[str, float, list[dict]]],
    fps: float,
    holds: dict,
    section_names: list[str],
) -> list[int]:
    """Per-line display windows = TTS duration + per-section hold seconds.

    Holds extend only the on-screen window (hook/caption/rank screens and
    their compose windows); the wav audio and the music bed keep the true
    TTS durations. Positive holds lengthen, negative holds shorten the
    window; floors at 1 frame (never 0 — a zero-length clip breaks ffmpeg).
    """
    return [
        max(
            1,
            round(
                (
                    duration
                    + holds.get(
                        section_names[idx] if idx < len(section_names) else "message",
                        0.0,
                    )
                )
                * fps
            ),
        )
        for idx, (_, duration, _) in enumerate(line_data)
    ]


# ── Background Generation ──────────────────────────────────────────────────────


def generate_background(output_path: str, width: int = REEL_WIDTH, height: int = REEL_HEIGHT):
    subprocess.run(
        ["convert", "-size", f"{width}x{height}", "gradient:#0a0a32-#280f46", output_path],
        capture_output=True,
        check=True,
    )


def generate_outro_clip(
    output_path: str,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    text: str = "Thanks for watching",
) -> None:
    """Generate the bundled default outro: a short gradient clip with
    subtle text, encoded at the reel's own fps so the compose path can use
    the full clip without frame-rate surprises.
    """
    img = Image.new("RGB", (width, height), (10, 10, 50))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width, height), fill=(10, 10, 50))
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 96)
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text(
        ((width - (bbox[2] - bbox[0])) / 2, (height - (bbox[3] - bbox[1])) / 2),
        text,
        font=font,
        fill=(255, 255, 255, 255),
    )
    frame_path = output_path + ".png"
    img.save(frame_path)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            frame_path,
            "-t",
            str(OUTRO_DEFAULT_SECONDS),
            "-vf",
            f"scale={width}:{height}",
            "-r",
            "30",
            "-an",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "h264_nvenc",
            output_path,
        ],
        capture_output=True,
        check=True,
    )
    os.unlink(frame_path)


_OUTRO_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _fit_outro_text(
    text: str,
    canvas_width: int,
    max_px: int = 96,
    min_px: int = 24,
):
    """Fit outro text to the canvas: shrink from ``max_px`` down to ``min_px``
    while the line is wider than 85% of the canvas, then word-wrap on spaces
    so every line fits. Returns ``(font, lines)`` for the clip builder."""
    probe = ImageDraw.Draw(Image.new("RGBA", (canvas_width, 16)))
    limit = int(canvas_width * 0.85)

    def shrink():
        px = max_px
        while px >= min_px:
            font = ImageFont.truetype(_OUTRO_FONT_PATH, px)
            bbox = probe.textbbox((0, 0), text, font=font)
            if bbox[2] - bbox[0] <= limit:
                return font, [text]
            px -= 4
        return None

    fitted = shrink()
    if fitted is not None:
        return fitted

    font = ImageFont.truetype(_OUTRO_FONT_PATH, min_px)
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = (current + " " + word).strip()
        bbox = probe.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= limit or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return font, lines


def _render_outro_text_clip(
    text: str,
    out_path: str,
    outro_seconds: float,
    fps: float,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
) -> None:
    """Render `text` centered on a transparent full-canvas clip the length
    of the outro window (qtrle, like the watermark overlay)."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font, lines = _fit_outro_text(text, width)
    line_h = font.size + 12
    block_h = len(lines) * line_h
    y0 = (height - block_h) / 2
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (width - (bbox[2] - bbox[0])) / 2
        y = y0 + i * line_h - bbox[1]
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_path = os.path.join(tmp_dir, "outro_text.png")
        img.save(frame_path)
        list_path = os.path.join(tmp_dir, "concat.txt")
        duration = outro_seconds
        with open(list_path, "w") as f:
            f.write(f"file '{frame_path}'\nduration {duration + 0.5:.3f}\n")
            f.write(f"file '{frame_path}'\n")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_path,
                "-pix_fmt",
                "argb",
                "-c:v",
                "qtrle",
                "-r",
                str(fps),
                out_path,
            ],
            capture_output=True,
            check=True,
        )


def _render_watermark_clip(
    watermark_path: str,
    out_path: str,
    total_frames: int,
    fps: float,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    render_config: RenderConfig | None = None,
) -> None:
    """Bake the watermark into a full-canvas transparent .mov: resized to a
    configurable percentage of the reel width, placed in a corner with a
    margin, alpha faded to a configurable opacity."""
    cfg = render_config or RenderConfig()
    img = Image.open(watermark_path).convert("RGBA")
    target_w = round(width * cfg.watermark_size_pct / 100)
    ratio = target_w / img.width
    img = img.resize((target_w, round(img.height * ratio)), Image.Resampling.LANCZOS)
    alpha = img.getchannel("A").point(lambda a: round(a * cfg.watermark_opacity))
    img.putalpha(alpha)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    margin = cfg.watermark_margin_px
    if cfg.watermark_corner == "bottom_left":
        pos = (margin, height - img.height - margin)
    elif cfg.watermark_corner == "top_right":
        pos = (width - img.width - margin, margin)
    elif cfg.watermark_corner == "top_left":
        pos = (margin, margin)
    else:
        pos = (width - img.width - margin, height - img.height - margin)
    canvas.paste(img, pos, img)
    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_path = os.path.join(tmp_dir, "wm.png")
        canvas.save(frame_path)
        list_path = os.path.join(tmp_dir, "concat.txt")
        duration = total_frames / fps
        with open(list_path, "w") as f:
            f.write(f"file '{frame_path}'\nduration {duration + 0.5:.3f}\n")
            f.write(f"file '{frame_path}'\n")
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            list_path,
            "-pix_fmt",
            "argb",
            "-c:v",
            "qtrle",
            "-r",
            str(fps),
            out_path,
        ]
        subprocess.run(cmd, capture_output=True, check=True)


def _bake_music_bed(
    music_path: str, out_path: str, total_seconds: float, fade_seconds: float = 2.0
) -> None:
    """Loop the music bed to the narration length with a configurable
    fade in/out."""
    fade_out_start = max(0.0, total_seconds - fade_seconds)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            music_path,
            "-t",
            f"{total_seconds:.3f}",
            "-af",
            f"afade=t=in:d={fade_seconds},afade=t=out:st={fade_out_start:.3f}:d={fade_seconds}",
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            out_path,
        ],
        capture_output=True,
        check=True,
    )


def _looped_gradient_video(
    png_path: str,
    video_path: str,
    total_seconds: float,
    fps: float,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
) -> None:
    """Loop a static gradient image into an MP4 of `total_seconds` length.

    The stock-video fallback background: encoded at the project's own fps so
    the compose path can use the full clip without frame-rate surprises
    (ffmpeg's default fps of 25 would silently mismatch the 30fps project).
    """
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            png_path,
            "-t",
            str(total_seconds + 1),
            "-vf",
            f"scale={width}:{height}",
            "-r",
            str(fps),
            "-an",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "h264_nvenc",
            video_path,
        ],
        capture_output=True,
        check=True,
    )


def _looped_image_video(
    img_path: str,
    video_path: str,
    total_seconds: float,
    fps: float,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
) -> None:
    """Loop a still image into an MP4 of `total_seconds` length, cover-cropped
    onto the reel canvas so the frame is always full-bleed."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            img_path,
            "-t",
            str(total_seconds + 1),
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
            "-r",
            str(fps),
            "-an",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "h264_nvenc",
            video_path,
        ],
        capture_output=True,
        check=True,
    )


def _loop_clip_to_duration(
    src_path: str,
    dst_path: str,
    total_seconds: float,
    fps: float,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
) -> None:
    """Loop a user clip (or trim it) so it covers exactly `total_seconds`,
    fitted (scaled+padded) onto the configured reel canvas."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            src_path,
            "-t",
            f"{total_seconds:.3f}",
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-r",
            str(fps),
            "-an",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            dst_path,
        ],
        capture_output=True,
        check=True,
    )


def _background_motion_vf(
    motion: str, fps: float, width: int = REEL_WIDTH, height: int = REEL_HEIGHT, frames: int = 2
) -> str:
    """Build the zoompan filter graph for a Ken Burns motion style. The input
    is upscaled 2x first so the zoompan crop lands on soft pixels, avoiding
    the sub-pixel jitter a 1:1 zoompan produces at reel resolutions."""
    if motion == "zoom":
        return (
            f"scale=iw*2:ih*2,zoompan=z='min(zoom+0.0004,1.15)':d=1:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps={fps}"
        )
    return (
        f"scale=iw*2:ih*2,zoompan=z=1.06:d=1:"
        f"x='(iw-iw/zoom)*on/{max(frames, 2)}':"
        f"y='ih/2-(ih/zoom/2)':s={width}x{height}:fps={fps}"
    )


def _apply_background_motion(path: str, motion: str, fps: float) -> str:
    """Re-encode a background clip with the configured Ken Burns motion;
    returns the original path when motion is off or the re-encode fails."""
    if motion == "none":
        return path
    frames = 2
    if motion == "pan":
        frames = max(round((stock_video._probe_duration(path) or 0.0) * fps), 2)
    out_path = os.path.splitext(path)[0] + "_motion.mp4"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                path,
                "-vf",
                _background_motion_vf(motion, fps, REEL_WIDTH, REEL_HEIGHT, frames),
                "-an",
                "-pix_fmt",
                "yuv420p",
                "-c:v",
                "libx264",
                out_path,
            ],
            capture_output=True,
            check=True,
        )
        return out_path
    except (subprocess.CalledProcessError, OSError) as exc:
        _log(f"   Background motion ({motion}) failed ({exc}), using original clip")
        return path


def _fit_clip_to_canvas(
    src_path: str, dst_path: str, fps: float, width: int = REEL_WIDTH, height: int = REEL_HEIGHT
) -> None:
    """Scale+pad a clip onto the configured reel canvas, preserving duration.

    Used for overlay layers (e.g. the outro asset) so a small/native-sized
    video fills the whole canvas instead of sitting at its raw size in the
    top-left corner of the overlay box.
    """
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            src_path,
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-r",
            str(fps),
            "-an",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            dst_path,
        ],
        capture_output=True,
        check=True,
    )


# ── Pipeline ───────────────────────────────────────────────────────────────────


class ReelPipeline:
    def __init__(
        self,
        quote: str = "",
        topic: str = "",
        attribution: str = "",
        output: str = "daily_success_reel.mp4",
        duration_seconds: float = DEFAULT_DURATION_SECONDS,
        render_timeout: int = RENDER_TIMEOUT,
        dev: bool = False,
        caption_style: str = "highlight",
        caption_styles: list[str] | None = None,
        reel_width: int = REEL_WIDTH,
        reel_height: int = REEL_HEIGHT,
        assets=None,
        progress_callback=None,
        owner: str = "",
        beat_provider=None,
        render_config: RenderConfig | None = None,
        stages: dict | None = None,
        stock_api_keys: dict | None = None,
        bg_source: str = "",
        bg_mode: str = "",
        stock_provider: str = "auto",
        outro_text: str = "",
        background_queries: list[str] | None = None,
        voice_preset: str = narration.DEFAULT_VOICE_PRESET,
        hook_lead_in_seconds: float = 0.0,
        rank_style: str = "number",
    ):
        if reel_width <= 0 or reel_height <= 0:
            raise ValueError(f"reel dimensions must be positive: {reel_width}x{reel_height}")
        self.owner = owner
        self.quote = quote
        self.topic = topic
        self.attribution = attribution
        self.output = os.path.abspath(output)
        self.duration_seconds = duration_seconds
        self.duration_frames = None  # computed from the compose plan
        self.render_timeout = render_timeout
        self.dev = dev
        self.caption_style = caption_style
        self.caption_styles = caption_styles if caption_styles is not None else ["highlight"]
        self.beat_provider = beat_provider
        self.reel_width = reel_width
        self.reel_height = reel_height
        self.assets = assets
        self.progress_callback = progress_callback
        self.render_config = render_config or RenderConfig()
        self.stages = stages or {}
        self.stock_api_keys = stock_api_keys or {}
        self.bg_source = bg_source or ""
        self.bg_mode = bg_mode or ""
        self.stock_provider = stock_provider or "auto"
        self.outro_text = outro_text or ""
        self.background_queries = list(background_queries or [])
        self.voice_preset = (
            voice_preset
            if voice_preset in narration.VOICE_PRESETS
            else narration.DEFAULT_VOICE_PRESET
        )
        self.hook_lead_in_seconds = hook_lead_in_seconds or 0.0
        self.rank_style = rank_style if rank_style in ("number", "check") else "number"
        self.script: ParsedScript | None = (
            None  # populated by _generate_script() when self.topic is set
        )
        self.idea: Idea | None = None  # set by main() when --idea-gen picks a winning idea
        self.seo_metadata: dict[str, str] | None = None  # populated after _generate_script()
        self.temp_dir = tempfile.mkdtemp(prefix="dsm_")
        os.chmod(self.temp_dir, 0o755)

    def cleanup(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _save_outputs(self):
        run_dir = getattr(self, "run_dir", None)
        if not run_dir:
            return
        import json as _json

        if self.idea:
            with open(os.path.join(run_dir, "idea.json"), "w") as f:
                _json.dump(
                    {
                        "title": self.idea.title,
                        "core_message": self.idea.core_message,
                        "hook_line": self.idea.hook_line,
                        "identity_signal": self.idea.identity_signal,
                        "permission_given": self.idea.permission_given,
                        "emotional_arc": self.idea.emotional_arc,
                        "target_audience": self.idea.target_audience,
                        "quotability_score": self.idea.quotability_score,
                        "share_trigger": self.idea.share_trigger,
                    },
                    f,
                    indent=2,
                )

        if self.script:
            with open(os.path.join(run_dir, "script.json"), "w") as f:
                _json.dump(
                    {
                        "title": self.script.title,
                        "duration_seconds": self.script.duration_seconds,
                        "word_count": self.script.word_count,
                        "pacing_wps": self.script.pacing_wps,
                        "hook": self.script.hook,
                        "hook_seconds": self.script.hook_seconds,
                        "message_lines": self.script.message_lines,
                        "message_seconds": self.script.message_seconds,
                        "metaphor": self.script.metaphor,
                        "metaphor_seconds": self.script.metaphor_seconds,
                        "conclusion": self.script.conclusion,
                        "conclusion_seconds": self.script.conclusion_seconds,
                        "emotional_arc": self.script.emotional_arc,
                        "parallel_structure": self.script.parallel_structure,
                        "hook_score": self.script.hook_score,
                    },
                    f,
                    indent=2,
                )

            # visual_prompts.json is unused downstream (background comes from
            # stock_video.py nature footage, not per-line generated images) - disabled for now
            # all_lines = ([self.script.hook] + self.script.message_lines
            #              + [self.script.metaphor, self.script.conclusion])
            # emotion = self.idea.emotional_arc if self.idea else ""
            # visual_prompts = []
            # for idx, line in enumerate(all_lines):
            #     vp = prompts.build_visual_prompt(line, emotion, idx)
            #     visual_prompts.append({"line": line, "scene_index": idx, "prompt": vp})
            # with open(os.path.join(run_dir, "visual_prompts.json"), "w") as f:
            #     _json.dump(visual_prompts, f, indent=2)

            with open(os.path.join(run_dir, "caption.txt"), "w") as f:
                f.write("Daily Success Mindset\n")
                f.write(f"Topic: {self.topic}\n\n")
                f.write(f"{self.script.hook}\n\n")
                f.writelines(f"{line}\n" for line in self.script.message_lines)
                f.write(f"\n{self.script.metaphor}\n")
                f.write(f"{self.script.conclusion}\n")

        if self.seo_metadata:
            seo_path = os.path.join(run_dir, "seo_metadata.json")
            with open(seo_path, "w") as f:
                _json.dump(self.seo_metadata, f, indent=2)
            _log(f"   SEO metadata saved: {seo_path}")

        _log(f"   Outputs saved to {run_dir}/")

    async def _generate_script(self):
        if self.script:
            return
        _log("Generating script...")
        title = self.idea.title if self.idea else self.topic
        core_message = self.idea.core_message if self.idea else self.topic
        target_emotion = (
            self.idea.emotional_arc
            if self.idea
            else "as appropriate for a self-improvement audience"
        )
        target_audience = (
            self.idea.target_audience if self.idea else "people working on personal growth"
        )

        _log("   Researching content angles...")
        angle_context = await research_content_angles(title, core_message, llm=None)
        prompts.build_scriptwriting_prompt(
            title=title,
            core_message=core_message,
            target_emotion=target_emotion,
            target_audience=target_audience,
            angle_context=angle_context,
        )
        _log("   LLM not available in pipeline — script must be set externally via self.script")
        return

    def _background_segments(
        self,
        line_data: list[tuple[str, float, list[dict]]],
        fps: float,
    ) -> list[tuple[str, int, int]]:
        """Segment boundaries by narrative mood, from cumulative line frames:
        hook / message block / metaphor+conclusion remainder. Only segments
        spanning more than 0.3s are kept (the rest are dropped)."""
        line_frames = held_line_frames(
            line_data,
            fps,
            self.render_config.section_holds,
            self.script.section_names if self.script else [],
        )
        if not line_frames:
            return []
        total = sum(line_frames)
        script = self.script
        hook_text = script.hook if script else ""
        msg_text = script.message_lines[0] if script and script.message_lines else ""
        end_text = (script.metaphor or script.conclusion) if script else ""
        parts = [(hook_text, 0, line_frames[0])]
        if len(line_frames) >= 3:
            msg_end = line_frames[0] + sum(line_frames[1 : len(line_frames) - 2])
            parts.append((msg_text, line_frames[0], msg_end))
            parts.append((end_text, msg_end, total))
        elif len(line_frames) == 2:
            parts.append((msg_text or end_text, line_frames[0], total))
        min_span_frames = 0.3 * fps
        return [p for p in parts if p[2] - p[1] > min_span_frames]

    async def _fetch_background_clip(self, total_frames: int, fps: float) -> str:
        segments = await self._fetch_background_segments([("", 0, total_frames)], fps)
        return segments[0][0]

    async def _fetch_background_segments(
        self,
        segments: list[tuple[str, int, int]],
        fps: float,
    ) -> list[tuple[str, int, int]]:
        """Fetch one stock clip per narrative segment (query chosen from the
        segment's first line), falling back to per-segment gradient clips
        for failed fetches, and to one full-length gradient when every
        segment fails. Returns [(path, start_frame, end_frame)] covering
        the full span of `segments`."""
        if self.bg_mode == "image":
            return await self._fetch_image_background_segment(segments, fps)
        if self.bg_source != "api":
            if self.assets and self.assets.bg_clip_path:
                video_path = os.path.join(self.temp_dir, "background_asset.mp4")
                try:
                    await asyncio.to_thread(
                        _loop_clip_to_duration,
                        self.assets.bg_clip_path,
                        video_path,
                        segments[-1][2] / fps,
                        fps,
                        self.reel_width,
                        self.reel_height,
                    )
                    motion_path = _apply_background_motion(
                        video_path, self.render_config.background_motion, fps
                    )
                    return [(motion_path, 0, segments[-1][2])]
                except (subprocess.CalledProcessError, OSError) as exc:
                    _log(f"   User background clip unusable ({exc}), using stock video")
            if SAMPLE_BACKGROUND.exists():
                video_path = os.path.join(self.temp_dir, "background_sample.mp4")
                try:
                    await asyncio.to_thread(
                        _loop_clip_to_duration,
                        str(SAMPLE_BACKGROUND),
                        video_path,
                        segments[-1][2] / fps,
                        fps,
                        self.reel_width,
                        self.reel_height,
                    )
                    _log(f"   Using bundled sample background ({SAMPLE_BACKGROUND.name})")
                    motion_path = _apply_background_motion(
                        video_path, self.render_config.background_motion, fps
                    )
                    return [(motion_path, 0, segments[-1][2])]
                except (subprocess.CalledProcessError, OSError) as exc:
                    _log(f"   Bundled sample background unusable ({exc}), using stock video")
        queries = self.background_queries or stock_video.DEFAULT_QUERIES

        async def _one(first_line: str, start: int, end: int) -> tuple[str, int, int]:
            path = os.path.join(self.temp_dir, f"background_stock_seg_{start}.mp4")
            ok = await stock_video.fetch_background_video(
                stock_video.query_for_line(first_line or "", queries),
                path,
                (end - start) / fps,
                width=self.reel_width,
                height=self.reel_height,
                fps=fps,
                category="nature",
                owner=self.owner,
                api_keys=self.stock_api_keys,
                provider=self.stock_provider,
            )
            if ok:
                motion_path = _apply_background_motion(
                    path, self.render_config.background_motion, fps
                )
                return (motion_path, start, end)
            return ("", start, end)

        results = await asyncio.gather(*[_one(*seg) for seg in segments])
        ok_paths = [res for res in results if res[0]]
        failed = [(s, e) for path, s, e in results if not path]
        if not ok_paths:
            _log("   Stock video unavailable for all segments, using gradient fallback")
            img_path = os.path.join(self.temp_dir, "background.png")
            generate_background(img_path, self.reel_width, self.reel_height)
            fallback_video_path = os.path.join(self.temp_dir, "background_fallback.mp4")
            await asyncio.to_thread(
                _looped_gradient_video,
                img_path,
                fallback_video_path,
                segments[-1][2] / fps,
                fps,
                self.reel_width,
                self.reel_height,
            )
            motion_path = _apply_background_motion(
                fallback_video_path, self.render_config.background_motion, fps
            )
            return [(motion_path, 0, segments[-1][2])]
        if failed:
            _log(
                f"   Stock video unavailable for {len(failed)} segment(s), "
                "using per-segment gradient fallback"
            )
            for start, end in failed:
                img_path = os.path.join(self.temp_dir, f"background_seg_{start}.png")
                generate_background(img_path, self.reel_width, self.reel_height)
                seg_path = os.path.join(self.temp_dir, f"background_fallback_{start}.mp4")
                await asyncio.to_thread(
                    _looped_gradient_video,
                    img_path,
                    seg_path,
                    (end - start) / fps,
                    fps,
                    self.reel_width,
                    self.reel_height,
                )
                motion_path = _apply_background_motion(
                    seg_path, self.render_config.background_motion, fps
                )
                ok_paths.append((motion_path, start, end))
        return sorted(ok_paths, key=lambda res: res[1])

    async def _fetch_image_background_segment(
        self,
        segments: list[tuple[str, int, int]],
        fps: float,
    ) -> list[tuple[str, int, int]]:
        """Image-background mode: loop the user image (cover-cropped) across
        the whole reel; without one, generate the gradient image. Ken Burns
        motion applies exactly as it does to video backgrounds. Never touches
        stock video or the bundled sample clip."""
        total_seconds = segments[-1][2] / fps
        fallback = os.path.join(self.temp_dir, "background_fallback.mp4")
        img_path = os.path.join(self.temp_dir, "background.png")
        if self.assets and self.assets.bg_clip_path:
            try:
                video_path = os.path.join(self.temp_dir, "background_image.mp4")
                await asyncio.to_thread(
                    _looped_image_video,
                    self.assets.bg_clip_path,
                    video_path,
                    total_seconds,
                    fps,
                    self.reel_width,
                    self.reel_height,
                )
                motion_path = _apply_background_motion(
                    video_path, self.render_config.background_motion, fps
                )
                return [(motion_path, 0, segments[-1][2])]
            except (subprocess.CalledProcessError, OSError) as exc:
                _log(f"   User background image unusable ({exc}), using gradient fallback")
        generate_background(img_path, self.reel_width, self.reel_height)
        await asyncio.to_thread(
            _looped_gradient_video,
            img_path,
            fallback,
            total_seconds,
            fps,
            self.reel_width,
            self.reel_height,
        )
        motion_path = _apply_background_motion(fallback, self.render_config.background_motion, fps)
        return [(motion_path, 0, segments[-1][2])]

    def _read_music_asset(self, music_path: str) -> MediaAsset:
        """Wrap the music file bytes in a local MediaAsset for beat analysis."""
        with open(music_path, "rb") as f:
            return MediaAsset(mime_type="audio/mpeg", provider="local", bytes_data=f.read())

    async def _bake_beat_locked_music(
        self,
        music_local: str,
        line_frames: list[int],
        fps: float,
        narration_seconds: float,
        outro_seconds: float,
    ) -> None:
        """Bake the beat-locked bed for formats declaring music_beat: analyze the
        music asset, phase-lock item 1 to a beat, apply energy automation. Any
        failure falls back to the plain looped bed so the render never
        crashes on beat features."""
        from lexigram.contracts.multimedia.types import BeatAnalysisRequest

        from shorts_creator.pipeline.music_beat import bake_beat_bed

        beats = None
        try:
            music_path = self.assets.music_path
            asset = await asyncio.to_thread(self._read_music_asset, music_path)
            result = await self.beat_provider.analyze(BeatAnalysisRequest(asset=asset))
            if result.is_ok():
                beats = result.unwrap().beat_timestamps
        except Exception as exc:  # noqa: BLE001 - beat features are best-effort
            _log(f"   Beat analysis unavailable ({exc}), using plain music bed")

        if not beats:
            await asyncio.to_thread(
                _bake_music_bed,
                self.assets.music_path,
                music_local,
                narration_seconds,
                self.render_config.music_fade_seconds,
            )
            return
        try:
            loop_seconds = float(stock_video._probe_duration(self.assets.music_path) or 0)
            item_starts = [sum(line_frames[:i]) / fps for i in range(1, min(6, len(line_frames)))]
            await asyncio.to_thread(
                bake_beat_bed,
                self.assets.music_path,
                music_local,
                loop_seconds,
                beats,
                item_starts,
                narration_seconds,
                narration_seconds + outro_seconds,
                fade_seconds=self.render_config.music_fade_seconds,
            )
        except Exception as exc:  # noqa: BLE001 - beat features are best-effort
            _log(f"   Beat bake failed ({exc}), using plain music bed")
            await asyncio.to_thread(
                _bake_music_bed,
                self.assets.music_path,
                music_local,
                narration_seconds,
                self.render_config.music_fade_seconds,
            )

    async def _synthesize_narration(self, lines: list[str]) -> list[tuple[str, float, list[dict]]]:
        """Synthesize one WAV per line via Chatterbox and pull real word
        timings via Whisper. Returns (wav_path, duration_seconds, words) per
        line - this replaces the LLM's estimated per-section durations as
        the source of truth for how long each line's clip actually needs to
        be.
        """
        _log(f"   Synthesizing narration for {len(lines)} lines...")
        wav_paths = [os.path.join(self.temp_dir, f"line_{idx}.wav") for idx in range(len(lines))]
        # synthesize_batch blocks on a subprocess.run call - run it in a thread
        # so it doesn't stall the event loop, otherwise the _fetch_background_clip
        # gather with narration synthesis would be serialized behind it
        # instead of actually running concurrently.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            functools.partial(
                narration.synthesize_batch, owner=self.owner, voice_preset=self.voice_preset
            ),
            lines,
            wav_paths,
        )
        durations = [narration.get_duration(wav_path) for wav_path in wav_paths]
        # Whisper runs CPU-only (see narration.get_word_timings), so these are
        # safe to fan out concurrently without contending with the GPU work
        # (Chatterbox/Ollama/NVENC) happening elsewhere in the pipeline.
        # Run the whole pass in one executor call: each line takes tens of
        # seconds, and doing it synchronously on the loop would stall SSE
        # heartbeats and every other HTTP request for minutes.
        words_lists = await loop.run_in_executor(
            None,
            functools.partial(narration.transcribe_all, owner=self.owner),
            wav_paths,
        )
        # Whisper's transcription text is not usable as captions (it garbles
        # the TTS voice, e.g. "The day" -> "W-day"), so realign each line's
        # timings onto the script's own words here - captions are built from
        # the returned words further down the pipeline.
        aligned_words = [
            narration.align_words(line, words, duration)
            for line, words, duration in zip(lines, words_lists, durations)
        ]
        return list(zip(wav_paths, durations, aligned_words))

    async def _push_progress(self, stage: str, progress: float, message: str):
        if self.progress_callback:
            await self.progress_callback(stage, progress, message)

    async def run(self):
        _log("Daily Success Mindset Reel Pipeline")
        if self.topic:
            _log(f"  Topic: {self.topic}")
        else:
            _log(f"  Quote: {self.quote}")
        if self.attribution:
            _log(f"  Attribution: {self.attribution}")
        _log(f"  Output: {self.output}")

        render_ok = True
        try:
            render_ok = await self._run_ffmpeg()
        finally:
            self.cleanup()

        if render_ok:
            _log(f"Done! Output: {self.output}")
        else:
            _log(f"Render did not complete - partial output (if any) at: {self.output}")
        return render_ok

    async def _run_ffmpeg(self):
        from lexigram.multimedia.timeline import Timeline
        from lexigram.multimedia.video.processing.ffmpeg import (
            FFmpegVideoProcessor,
            VideoProcessingConfig,
        )

        from shorts_creator.pipeline.compose import (
            build_compose_plan,
            caption_chunk_windows,
            chunk_word_frames,
            hook_font_size,
        )

        if self.topic:
            await self._generate_script()
        if self.script is None:
            _log("   No script set and none could be generated (LLM unavailable)")
            raise RuntimeError(
                "No script available for render — generate a script first "
                "(the LLM provider may be offline)."
            )
        await self._push_progress("outputs", 0.0, "Saving outputs...")
        self._save_outputs()
        await self._push_progress("outputs", 1.0, "Outputs saved")
        await self._push_progress("project", 0.0, "Preparing project...")
        await self._push_progress("project", 1.0, "Project ready")

        script = self.script
        fps = 30.0
        font_path = self.assets.font_path if self.assets else None
        all_lines = (
            [script.hook]
            + list(script.top_items)
            + list(script.message_lines)
            + [script.metaphor, script.conclusion]
        )

        await self._push_progress(
            "timeline", 0.0, "Fetching background and synthesizing narration..."
        )
        line_data = await self._synthesize_narration(all_lines)
        if self.hook_lead_in_seconds > 0 and line_data:
            lead = self.hook_lead_in_seconds
            wav0, dur0, words0 = line_data[0]
            padded = os.path.join(self.temp_dir, "line_0_padded.wav")
            await asyncio.to_thread(
                narration.prepend_silence,
                wav0,
                lead,
                padded,
                self.owner,
            )
            words0 = [
                {"word": w["word"], "start": w["start"] + lead, "end": w["end"] + lead}
                for w in words0
            ]
            line_data[0] = (padded, dur0 + lead, words0)
        if self.stages.get("background") is False:
            bg_segments: list[tuple[str, int, int]] = []
        else:
            bg_segments = await self._fetch_background_segments(
                self._background_segments(line_data, fps),
                fps,
            )
        line_frames = held_line_frames(
            line_data,
            fps,
            self.render_config.section_holds,
            self.script.section_names if self.script else [],
        )
        _log(f"   Narration + background fetch done ({sum(line_frames)} narration frames)")
        await self._push_progress("timeline", 0.25, "Background and narration ready")

        caption_groups_by_idx: dict[int, list[list[dict]]] = {}
        ranked = not self.caption_styles and bool(script.top_items) and len(line_data) > 0
        if self.caption_styles or ranked:
            if self.caption_styles:
                await self._push_progress("timeline", 0.3, "Grouping captions...")
                for idx in range(1, len(line_data)):
                    caption_groups_by_idx[idx] = await captions.group_by_thought(
                        all_lines[idx], line_data[idx][2], None
                    )

            hook_words = line_data[0][2]
            if not hook_words:
                hook_words = [{"word": all_lines[0], "start": 0.0, "end": line_data[0][1]}]
            hook_texts = [
                " ".join(w["word"] for w in chunk)
                for chunk in captions.group_for_hook_display(
                    hook_words, self.render_config.hook_line_target_size
                )
            ]
            hook_path = os.path.join(self.temp_dir, "hook.mov")
            await asyncio.to_thread(
                _render_hook_clip,
                hook_texts,
                hook_font_size(hook_texts, self.reel_width, self.reel_height, self.render_config),
                fps,
                line_frames[0],
                hook_path,
                font_path,
                self.reel_width,
                self.reel_height,
                render_config=self.render_config,
            )

            if self.caption_styles:
                await self._push_progress("timeline", 0.4, "Baking caption clips...")
                section_names = script.section_names
                for idx in range(1, len(line_data)):
                    _, duration, words = line_data[idx]
                    if not words:
                        words = [{"word": all_lines[idx], "start": 0.0, "end": duration}]
                    groups = caption_groups_by_idx[idx]
                    chunks = [
                        chunk[i : i + self.render_config.caption_max_words]
                        for chunk in groups
                        for i in range(0, len(chunk), self.render_config.caption_max_words)
                    ]
                    windows = caption_chunk_windows(chunks, words, fps, line_frames[idx])
                    for chunk_idx, (chunk, seg_start_rel, seg_end_rel) in enumerate(windows):
                        chunk_words = [w["word"] for w in chunk]
                        word_frames = chunk_word_frames(
                            chunk, seg_start_rel, seg_end_rel, fps, line_frames[idx]
                        )
                        font_size = _fit_caption_font_size(
                            chunk_words,
                            self.render_config.caption_font_size,
                            font_path,
                            self.reel_width,
                        )
                        chunk_path = os.path.join(self.temp_dir, f"caption_{idx}_{chunk_idx}.mov")
                        section = section_names[idx] if idx < len(section_names) else None
                        accent = self.render_config.stage_accents.get(section)
                        await asyncio.to_thread(
                            _render_caption_clip,
                            chunk_words,
                            word_frames,
                            fps,
                            font_size,
                            chunk_path,
                            True,
                            self.caption_style,
                            font_path,
                            self.reel_width,
                            self.reel_height,
                            render_config=self.render_config,
                            highlight_colour=accent,
                            emphasize=set(self.script.emphasis),
                        )
            else:
                await self._push_progress("timeline", 0.4, "Baking ranked item screens...")
                if self.caption_style == "list":
                    items_n = min(len(script.top_items), len(line_data) - 1)
                    seg_frames = sum(line_frames[1 : items_n + 1])
                    if seg_frames > 0:
                        items = []
                        for i in range(1, items_n + 1):
                            item_words = (
                                [w["word"] for w in line_data[i][2]]
                                if i < len(line_data) and line_data[i][2]
                                else script.top_items[i - 1].split()
                            )
                            items.append((str(i), " ".join(item_words)))
                        font_size = hook_font_size(
                            [text for _, text in items],
                            self.reel_width,
                            self.reel_height,
                            self.render_config,
                        )
                        list_path = os.path.join(self.temp_dir, "list.mov")
                        await asyncio.to_thread(
                            _render_list_clip,
                            items,
                            font_size,
                            fps,
                            seg_frames,
                            list_path,
                            font_path,
                            self.reel_width,
                            self.reel_height,
                            render_config=self.render_config,
                        )
                else:
                    render_rank = _rank_render_clip(self.rank_style)
                    for i in range(1, len(script.top_items) + 1):
                        item_words = (
                            [w["word"] for w in line_data[i][2]]
                            if i < len(line_data) and line_data[i][2]
                            else script.top_items[i - 1].split()
                        )
                        font_size = hook_font_size(
                            [str(i)] + item_words,
                            self.reel_width,
                            self.reel_height,
                            self.render_config,
                        )
                        rank_path = os.path.join(self.temp_dir, f"rank_{i}.mov")
                        await asyncio.to_thread(
                            render_rank,
                            str(i),
                            item_words,
                            font_size,
                            fps,
                            line_frames[i],
                            rank_path,
                            font_path,
                            self.reel_width,
                            self.reel_height,
                            render_config=self.render_config,
                        )

        outro_path = (
            self.assets.outro_clip_path
            if self.assets and self.assets.outro_clip_path
            else OUTRO_DEFAULT_PATH
        )
        if self.stages.get("outro") is False:
            outro_path = OUTRO_DEFAULT_PATH
        if self.outro_text and outro_path == OUTRO_DEFAULT_PATH:
            outro_path = os.path.join(self.temp_dir, "outro_default.mp4")
        if not os.path.exists(outro_path):
            if outro_path != OUTRO_DEFAULT_PATH:
                _log(f"   Outro asset missing at {outro_path!r}, falling back to default")
                outro_path = OUTRO_DEFAULT_PATH
            if self.outro_text:
                outro_path = os.path.join(self.temp_dir, "outro_default.mp4")
            if not os.path.exists(outro_path):
                _log("   Generating default outro clip...")
                await asyncio.to_thread(
                    generate_outro_clip,
                    outro_path,
                    self.reel_width,
                    self.reel_height,
                    self.outro_text or "Thanks for watching",
                )
        outro_seconds = stock_video._probe_duration(outro_path) or OUTRO_DEFAULT_SECONDS
        outro_frames = round(outro_seconds * fps)

        outro_text_path = ""
        if (
            self.outro_text
            and outro_path
            and os.path.basename(outro_path) != "outro_default.mp4"
            and os.path.exists(outro_path)
        ):
            outro_text_path = os.path.join(self.temp_dir, "outro_text.mov")
            await asyncio.to_thread(
                _render_outro_text_clip,
                self.outro_text,
                outro_text_path,
                outro_seconds,
                fps,
                self.reel_width,
                self.reel_height,
            )

        # Fit the outro onto the reel canvas. overlay keeps the layer's native
        # size, so an asset at any other resolution would render small in the
        # top-left corner of the frame instead of covering the full screen.
        if os.path.exists(outro_path):
            outro_fitted = os.path.join(self.temp_dir, "outro_fitted.mp4")
            await asyncio.to_thread(
                _fit_clip_to_canvas,
                outro_path,
                outro_fitted,
                fps,
                self.reel_width,
                self.reel_height,
            )
            outro_path = outro_fitted

        narration_seconds = sum(duration for _, duration, _ in line_data) / fps
        watermark_rel = ""
        if self.assets and self.assets.watermark_path and self.stages.get("watermark") is not False:
            wm_local = os.path.join(self.temp_dir, "watermark.mov")
            await asyncio.to_thread(
                _render_watermark_clip,
                self.assets.watermark_path,
                wm_local,
                round(sum(line_frames) + outro_frames),
                fps,
                self.reel_width,
                self.reel_height,
                render_config=self.render_config,
            )
            watermark_rel = wm_local
        music_rel = ""
        if self.assets and self.assets.music_path and self.stages.get("music") is not False:
            music_local = os.path.join(self.temp_dir, "music_bed.wav")
            if self.beat_provider is not None:
                await self._bake_beat_locked_music(
                    music_local,
                    line_frames,
                    fps,
                    narration_seconds,
                    outro_seconds,
                )
            else:
                await asyncio.to_thread(
                    _bake_music_bed,
                    self.assets.music_path,
                    music_local,
                    narration_seconds,
                    self.render_config.music_fade_seconds,
                )
            music_rel = music_local

        plan = build_compose_plan(
            script,
            line_data,
            "",
            fps,
            temp_dir=self.temp_dir,
            caption_groups_by_idx=caption_groups_by_idx,
            caption_styles=self.caption_styles,
            caption_style=self.caption_style,
            bg_segments=bg_segments,
            outro_path=outro_path,
            outro_seconds=outro_seconds,
            outro_text_path=outro_text_path,
            watermark_path=watermark_rel,
            music_bed_path=music_rel,
            width=self.reel_width,
            height=self.reel_height,
            render_config=self.render_config,
            stages=self.stages,
        )
        black_path = os.path.join(self.temp_dir, "black_base.mp4")
        await asyncio.to_thread(self._make_black_base, black_path, plan.total_frames, fps)

        timeline = Timeline()
        timeline.add_clip(plan.base_asset)
        for layer in plan.overlays:
            timeline.add_overlay(
                layer.asset,
                start=layer.start,
                end=layer.end,
                fade_in=layer.fade_in,
                fade_out=layer.fade_out,
            )
        for audio in plan.audio_layers:
            timeline.add_audio(audio.asset, start=audio.start, volume=audio.volume)
        timeline.set_fade_in(plan.fade_in).set_fade_out(plan.fade_out).set_encode(plan.encode)

        run_dir = getattr(self, "run_dir", None)
        if run_dir:
            recipe_path = os.path.join(run_dir, "timeline_recipe.json")
            await asyncio.to_thread(self._write_recipe, recipe_path, timeline.to_params())

        await self._push_progress("timeline", 1.0, "Timeline assembly complete")

        processor = FFmpegVideoProcessor(
            config=VideoProcessingConfig(
                temp_dir=self.temp_dir,
                timeout=self.render_timeout,
            )
        )
        loop = asyncio.get_running_loop()
        self._progress_tasks: set[asyncio.Task] = set()
        _sync_progress = self._make_progress_bridge(loop)

        result = await timeline.render(processor, progress_callback=_sync_progress)
        if result.is_err():
            err = result.unwrap_err()
            _log(f"   ffmpeg render failed: {err}")
            await self._push_progress("render", 0.0, f"Render failed: {err}")
            return False

        render_temp = os.path.join(self.temp_dir, "render_output.mp4")
        await asyncio.to_thread(
            self._write_render_output, render_temp, result.unwrap().bytes_data or b""
        )
        shutil.copy2(render_temp, self.output)
        os.chmod(self.output, 0o644)
        if self.render_config.audio_normalize:
            await self._loudnorm_output()
        self.duration_frames = plan.total_frames
        await self._push_progress("render", 1.0, "Render complete")
        await self._push_progress("finalize", 0.0, "Extracting screenshots...")
        await asyncio.to_thread(self._extract_screenshots)
        await self._push_progress("finalize", 0.5, "Transcoding 720p...")
        await asyncio.to_thread(self._transcode_720p)
        await self._push_progress("finalize", 1.0, "Finalized")
        return True

    def _make_progress_bridge(self, loop: asyncio.AbstractEventLoop) -> Callable[[float], None]:
        """Return a sync progress callback bridging to the async SSE stage
        emitter (design §4.3). Task refs are kept to satisfy RUF006.
        """

        def _sync_progress(pct: float) -> None:
            task = loop.create_task(
                self._push_progress("render", pct, f"Rendering: {int(pct * 100)}%")
            )
            self._progress_tasks.add(task)
            task.add_done_callback(self._progress_tasks.discard)

        return _sync_progress

    def _write_recipe(self, path: str, params: dict) -> None:
        import json as _json

        with open(path, "w") as f:
            _json.dump(params, f, indent=2)

    def _write_render_output(self, path: str, data: bytes) -> None:
        with open(path, "wb") as fh:
            fh.write(data)

    def _make_black_base(self, path: str, total_frames: int, fps: float) -> None:
        """Encode a full-length black video clip (design §5.3) via ffmpeg."""
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=black:size={self.reel_width}x{self.reel_height}:rate={fps}",
                "-t",
                str(total_frames / fps),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                path,
            ],
            capture_output=True,
            check=True,
        )

    async def _loudnorm_output(self) -> None:
        """Remux the master with Loudness-normalized AAC audio."""
        probe = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            self.output,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await probe.communicate()
        if probe.returncode != 0 or b"audio" not in stdout:
            _log("   No audio stream; skipping loudnorm pass")
            return
        tmp = f"{self.output}.loudnorm.mp4"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            self.output,
            "-c:v",
            "copy",
            "-af",
            f"loudnorm=I={self.render_config.loudness_target_lufs}:TP=-1.5:LRA=11",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            tmp,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        if proc.returncode == 0 and os.path.exists(tmp):
            os.replace(tmp, self.output)
            _log(f"   Loudness normalized to {self.render_config.loudness_target_lufs} LUFS")
        else:
            _log("   Loudnorm pass failed; keeping original audio")

    def _transcode_720p(self):
        """Write a 720px-wide H.264 companion next to the master file - FB
        Reels loads faster with a smaller H.264 file than the HEVC master.
        Aspect ratio follows the configured reel canvas (720x1280 for the
        default 1080x1920).
        """
        out_720 = self.output.replace(".mp4", "_720p.mp4")
        cmd = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            self.output,
            "-vf",
            "scale=min(720\\,iw):-2",
            "-c:v",
            "h264_nvenc",
            "-b:v",
            "2.5M",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            out_720,
        ]
        try:
            subprocess.run(cmd, check=True, timeout=180)
            _log(f"   720p variant: {out_720}")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
            _log(f"   720p transcode failed: {exc}")

    def _extract_screenshots(self, count: int = 3):
        """Grab `count` evenly-spaced JPEG stills from the finished render
        into run_dir, so the output folder has a quick visual preview
        without opening the video."""
        run_dir = getattr(self, "run_dir", None) or os.path.dirname(self.output)
        if not os.path.exists(self.output):
            return
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                self.output,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        duration = float(probe.stdout.strip())
        for i in range(count):
            timestamp = duration * (i + 1) / (count + 1)
            shot_path = os.path.join(run_dir, f"screenshot_{i + 1}.jpg")
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    str(timestamp),
                    "-i",
                    self.output,
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
                    shot_path,
                ],
                capture_output=True,
                check=True,
            )
        _log(f"   Screenshots saved to {run_dir}/")
