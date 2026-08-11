"""Daily Success Mindset — Short-form Reel Pipeline.

Orchestrates end-to-end reel creation: LLM script generation, TTS narration,
stock video sourcing, caption rendering, and ffmpeg compose render.
"""

import os

from shorts_creator.services.asset_service import ASSETS_ROOT

REEL_WIDTH = 1080
REEL_HEIGHT = 1920
SAMPLE_BACKGROUND = ASSETS_ROOT / "clip" / "sample_nature_asmr.mp4"
DEFAULT_DURATION_SECONDS = 30
RENDER_TIMEOUT = 600  # seconds - scripts now run 38-50s (up from 20-29s),
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
