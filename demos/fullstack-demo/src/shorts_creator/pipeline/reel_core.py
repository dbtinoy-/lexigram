"""Daily Success Mindset — Short-form Reel Pipeline.

Orchestrates end-to-end reel creation: LLM script generation, TTS narration,
stock video sourcing, caption rendering, and ffmpeg compose render.
"""

import os
import shutil
import tempfile

from shorts_creator.pipeline import constants, log
from shorts_creator.pipeline.render_config import RenderConfig
from shorts_creator.pipeline.script_parser import ParsedScript
from shorts_creator.topics.base import Idea

from . import narration, prompts
from .seo import research_content_angles


class ReelCoreMixin:
    """Mixin contributing reel pipeline methods for ReelPipeline."""

    def __init__(
        self,
        quote: str = "",
        topic: str = "",
        attribution: str = "",
        output: str = "daily_success_reel.mp4",
        duration_seconds: float = constants.DEFAULT_DURATION_SECONDS,
        render_timeout: int = constants.RENDER_TIMEOUT,
        dev: bool = False,
        caption_style: str = "highlight",
        caption_styles: list[str] | None = None,
        reel_width: int = constants.REEL_WIDTH,
        reel_height: int = constants.REEL_HEIGHT,
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
            log._log(f"   SEO metadata saved: {seo_path}")

        log._log(f"   Outputs saved to {run_dir}/")

    async def _generate_script(self):
        if self.script:
            return
        log._log("Generating script...")
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

        log._log("   Researching content angles...")
        angle_context = await research_content_angles(title, core_message, llm=None)
        prompts.build_scriptwriting_prompt(
            title=title,
            core_message=core_message,
            target_emotion=target_emotion,
            target_audience=target_audience,
            angle_context=angle_context,
        )
        log._log("   LLM not available in pipeline — script must be set externally via self.script")
        return

    async def _push_progress(self, stage: str, progress: float, message: str):
        if self.progress_callback:
            await self.progress_callback(stage, progress, message)

    async def run(self):
        log._log("Daily Success Mindset Reel Pipeline")
        if self.topic:
            log._log(f"  Topic: {self.topic}")
        else:
            log._log(f"  Quote: {self.quote}")
        if self.attribution:
            log._log(f"  Attribution: {self.attribution}")
        log._log(f"  Output: {self.output}")

        render_ok = True
        try:
            render_ok = await self._run_ffmpeg()
        finally:
            self.cleanup()

        if render_ok:
            log._log(f"Done! Output: {self.output}")
        else:
            log._log(f"Render did not complete - partial output (if any) at: {self.output}")
        return render_ok
