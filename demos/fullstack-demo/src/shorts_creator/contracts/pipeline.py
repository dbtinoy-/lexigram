from __future__ import annotations

"""The ONLY source of truth for which pipeline stages exist today.

A format may only require capabilities present in ``PIPELINE_CAPABILITIES``;
requiring anything else fails at load. ``FUTURE_PIPELINE_CAPABILITIES`` lists
names reserved for stages that do not yet exist — declaring them is invalid
until the stage lands and the entry is moved into the implemented map.
"""

PIPELINE_CAPABILITIES: dict[str, str] = {
    "word_timing": "pipeline/narration.py: align_words",
    "captions": "pipeline/captions.py: chunk rendering",
    "background": "pipeline/stock_video.py + gradient",
    "outro": "pipeline/pipeline.py: _generate_outro_clip",
    "tts_story": "pipeline/narration.py: synthesize_batch",
    "music_beat": "pipeline/music_beat.py: analyze + bake energy bed",
    "ranked_screens": "pipeline/pipeline.py: _render_ranked_clip bake",
}

FUTURE_PIPELINE_CAPABILITIES: frozenset[str] = frozenset({"silent_frames", "screen_tutorial"})
