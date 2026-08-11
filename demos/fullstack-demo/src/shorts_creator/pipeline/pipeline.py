"""Daily Success Mindset - Short-form Reel Pipeline (facade module).

The implementation lives in sibling modules (``log``, ``geometry``,
``caption_text``, ``constants``, ``outro``, ``background``, ``bake``,
``reel``). This module keeps the stable ``shorts_creator.pipeline.pipeline``
import path and re-exports the module-level attributes and helpers the
pipeline, its submodules, and its tests rely on.
"""

import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

from shorts_creator.pipeline import captions, narration, prompts, stock_video
from shorts_creator.pipeline.background import (
    _apply_background_motion,
    _background_motion_vf,
    _fit_clip_to_canvas,
    _looped_gradient_video,
    _looped_image_video,
    generate_background,
)
from shorts_creator.pipeline.bake import (
    _bake_music_bed,
    _loop_clip_to_duration,
    _render_watermark_clip,
)
from shorts_creator.pipeline.caption_text import (
    RANKED_NUMBER_SCALE,
    _bake_static_clip,
    _centered_row_geometry,
    _rank_render_clip,
    _render_caption_clip,
    _render_caption_frame,
    _render_checked_clip,
    _render_checked_frame,
    _render_hook_clip,
    _render_hook_frame,
    _render_list_clip,
    _render_list_frame,
    _render_ranked_clip,
    _render_ranked_frame,
)
from shorts_creator.pipeline.constants import (
    CAPTION_HIGHLIGHT_COLOUR,
    DEFAULT_DURATION_SECONDS,
    FADE_IN_SECONDS,
    FADE_OUT_SECONDS,
    OUTRO_DEFAULT_PATH,
    OUTRO_DEFAULT_SECONDS,
    REEL_HEIGHT,
    REEL_WIDTH,
    SAMPLE_BACKGROUND,
    held_line_frames,
)
from shorts_creator.pipeline.geometry import (
    _avg_char_width_px,
    _bold_font,
    _draw_pill,
    _fit_caption_font_size,
    _rgba_from_hex_colour,
    _text_width_px,
    _word_key,
    _wrap_lines,
)
from shorts_creator.pipeline.log import add_log_tee, remove_log_tee
from shorts_creator.pipeline.outro import (
    _fit_outro_text,
    _render_outro_text_clip,
    generate_outro_clip,
)
from shorts_creator.pipeline.reel import ReelPipeline

__all__ = [
    # constants
    "CAPTION_HIGHLIGHT_COLOUR",
    "DEFAULT_DURATION_SECONDS",
    "FADE_IN_SECONDS",
    "FADE_OUT_SECONDS",
    "OUTRO_DEFAULT_PATH",
    "OUTRO_DEFAULT_SECONDS",
    "RANKED_NUMBER_SCALE",
    "REEL_HEIGHT",
    "REEL_WIDTH",
    "SAMPLE_BACKGROUND",
    # module attributes kept for the pipeline's tests (monkeypatch targets)
    "Image",
    "ImageDraw",
    "ImageFont",
    # helpers / pipeline surface
    "ReelPipeline",
    "_apply_background_motion",
    "_avg_char_width_px",
    "_background_motion_vf",
    "_bake_music_bed",
    "_bake_static_clip",
    "_bold_font",
    "_centered_row_geometry",
    "_draw_pill",
    "_fit_caption_font_size",
    "_fit_clip_to_canvas",
    "_fit_outro_text",
    "_loop_clip_to_duration",
    "_looped_gradient_video",
    "_looped_image_video",
    "_rank_render_clip",
    "_render_caption_clip",
    "_render_caption_frame",
    "_render_checked_clip",
    "_render_checked_frame",
    "_render_hook_clip",
    "_render_hook_frame",
    "_render_list_clip",
    "_render_list_frame",
    "_render_outro_text_clip",
    "_render_ranked_clip",
    "_render_ranked_frame",
    "_render_watermark_clip",
    "_rgba_from_hex_colour",
    "_text_width_px",
    "_word_key",
    "_wrap_lines",
    "add_log_tee",
    "captions",
    "generate_background",
    "generate_outro_clip",
    "held_line_frames",
    "narration",
    "os",
    "prompts",
    "remove_log_tee",
    "stock_video",
    "subprocess",
]
