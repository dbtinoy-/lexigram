"""Daily Success Mindset — Short-form Reel Pipeline.

Orchestrates end-to-end reel creation: LLM script generation, TTS narration,
stock video sourcing, caption rendering, and ffmpeg compose render.
"""

import asyncio
import os
import shutil
from collections.abc import Callable

from shorts_creator.pipeline import background, bake, caption_text, constants, geometry, log, outro

from . import captions, narration, stock_video


class ReelComposeMixin:
    """Mixin contributing reel pipeline methods for ReelPipeline."""

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
            log._log("   No script set and none could be generated (LLM unavailable)")
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
        line_frames = constants.held_line_frames(
            line_data,
            fps,
            self.render_config.section_holds,
            self.script.section_names if self.script else [],
        )
        log._log(f"   Narration + background fetch done ({sum(line_frames)} narration frames)")
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
                caption_text._render_hook_clip,
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
                        font_size = geometry._fit_caption_font_size(
                            chunk_words,
                            self.render_config.caption_font_size,
                            font_path,
                            self.reel_width,
                        )
                        chunk_path = os.path.join(self.temp_dir, f"caption_{idx}_{chunk_idx}.mov")
                        section = section_names[idx] if idx < len(section_names) else None
                        accent = self.render_config.stage_accents.get(section)
                        await asyncio.to_thread(
                            caption_text._render_caption_clip,
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
                            caption_text._render_list_clip,
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
                    render_rank = caption_text._rank_render_clip(self.rank_style)
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
            else constants.OUTRO_DEFAULT_PATH
        )
        if self.stages.get("outro") is False:
            outro_path = constants.OUTRO_DEFAULT_PATH
        if self.outro_text and outro_path == constants.OUTRO_DEFAULT_PATH:
            outro_path = os.path.join(self.temp_dir, "outro_default.mp4")
        if not os.path.exists(outro_path):
            if outro_path != constants.OUTRO_DEFAULT_PATH:
                log._log(f"   Outro asset missing at {outro_path!r}, falling back to default")
                outro_path = constants.OUTRO_DEFAULT_PATH
            if self.outro_text:
                outro_path = os.path.join(self.temp_dir, "outro_default.mp4")
            if not os.path.exists(outro_path):
                log._log("   Generating default outro clip...")
                await asyncio.to_thread(
                    outro.generate_outro_clip,
                    outro_path,
                    self.reel_width,
                    self.reel_height,
                    self.outro_text or "Thanks for watching",
                )
        outro_seconds = stock_video._probe_duration(outro_path) or constants.OUTRO_DEFAULT_SECONDS
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
                outro._render_outro_text_clip,
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
                background._fit_clip_to_canvas,
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
                bake._render_watermark_clip,
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
                    bake._bake_music_bed,
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
            log._log(f"   ffmpeg render failed: {err}")
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
