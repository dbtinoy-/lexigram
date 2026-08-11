"""Daily Success Mindset — Short-form Reel Pipeline.

Orchestrates end-to-end reel creation: LLM script generation, TTS narration,
stock video sourcing, caption rendering, and ffmpeg compose render.
"""

import os
import subprocess
import tempfile

from PIL import Image, ImageDraw

from shorts_creator.pipeline.constants import (
    HOOK_LINE_HEIGHT_FACTOR,
    REEL_HEIGHT,
    REEL_WIDTH,
)
from shorts_creator.pipeline.geometry import (
    _HIGHLIGHT_PAD_PX,
    _bold_font,
    _draw_pill,
    _rgba_from_hex_colour,
    _word_key,
)
from shorts_creator.pipeline.render_config import RenderConfig


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
