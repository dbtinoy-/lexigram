"""Daily Success Mindset — Short-form Reel Pipeline.

Orchestrates end-to-end reel creation: LLM script generation, TTS narration,
stock video sourcing, caption rendering, and ffmpeg compose render.
"""

from shorts_creator.pipeline.reel_assets import ReelAssetsMixin
from shorts_creator.pipeline.reel_background import ReelBackgroundMixin
from shorts_creator.pipeline.reel_compose import ReelComposeMixin
from shorts_creator.pipeline.reel_core import ReelCoreMixin
from shorts_creator.pipeline.reel_finalize import ReelFinalizeMixin


class ReelPipeline(
    ReelCoreMixin, ReelBackgroundMixin, ReelAssetsMixin, ReelComposeMixin, ReelFinalizeMixin
):
    """End-to-end reel creation pipeline (facade over mixin modules)."""
