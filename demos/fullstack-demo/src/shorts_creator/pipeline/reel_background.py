"""Daily Success Mindset — Short-form Reel Pipeline.

Orchestrates end-to-end reel creation: LLM script generation, TTS narration,
stock video sourcing, caption rendering, and ffmpeg compose render.
"""

import asyncio
import os
import subprocess

from shorts_creator.pipeline import background, bake, constants, log

from . import stock_video


class ReelBackgroundMixin:
    """Mixin contributing reel pipeline methods for ReelPipeline."""

    def _background_segments(
        self,
        line_data: list[tuple[str, float, list[dict]]],
        fps: float,
    ) -> list[tuple[str, int, int]]:
        """Segment boundaries by narrative mood, from cumulative line frames:
        hook / message block / metaphor+conclusion remainder. Only segments
        spanning more than 0.3s are kept (the rest are dropped)."""
        line_frames = constants.held_line_frames(
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
                        bake._loop_clip_to_duration,
                        self.assets.bg_clip_path,
                        video_path,
                        segments[-1][2] / fps,
                        fps,
                        self.reel_width,
                        self.reel_height,
                    )
                    motion_path = background._apply_background_motion(
                        video_path, self.render_config.background_motion, fps
                    )
                    return [(motion_path, 0, segments[-1][2])]
                except (subprocess.CalledProcessError, OSError) as exc:
                    log._log(f"   User background clip unusable ({exc}), using stock video")
            if constants.SAMPLE_BACKGROUND.exists():
                video_path = os.path.join(self.temp_dir, "background_sample.mp4")
                try:
                    await asyncio.to_thread(
                        bake._loop_clip_to_duration,
                        str(constants.SAMPLE_BACKGROUND),
                        video_path,
                        segments[-1][2] / fps,
                        fps,
                        self.reel_width,
                        self.reel_height,
                    )
                    log._log(
                        f"   Using bundled sample background ({constants.SAMPLE_BACKGROUND.name})"
                    )
                    motion_path = background._apply_background_motion(
                        video_path, self.render_config.background_motion, fps
                    )
                    return [(motion_path, 0, segments[-1][2])]
                except (subprocess.CalledProcessError, OSError) as exc:
                    log._log(f"   Bundled sample background unusable ({exc}), using stock video")
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
                motion_path = background._apply_background_motion(
                    path, self.render_config.background_motion, fps
                )
                return (motion_path, start, end)
            return ("", start, end)

        results = await asyncio.gather(*[_one(*seg) for seg in segments])
        ok_paths = [res for res in results if res[0]]
        failed = [(s, e) for path, s, e in results if not path]
        if not ok_paths:
            log._log("   Stock video unavailable for all segments, using gradient fallback")
            img_path = os.path.join(self.temp_dir, "background.png")
            background.generate_background(img_path, self.reel_width, self.reel_height)
            fallback_video_path = os.path.join(self.temp_dir, "background_fallback.mp4")
            await asyncio.to_thread(
                background._looped_gradient_video,
                img_path,
                fallback_video_path,
                segments[-1][2] / fps,
                fps,
                self.reel_width,
                self.reel_height,
            )
            motion_path = background._apply_background_motion(
                fallback_video_path, self.render_config.background_motion, fps
            )
            return [(motion_path, 0, segments[-1][2])]
        if failed:
            log._log(
                f"   Stock video unavailable for {len(failed)} segment(s), "
                "using per-segment gradient fallback"
            )
            for start, end in failed:
                img_path = os.path.join(self.temp_dir, f"background_seg_{start}.png")
                background.generate_background(img_path, self.reel_width, self.reel_height)
                seg_path = os.path.join(self.temp_dir, f"background_fallback_{start}.mp4")
                await asyncio.to_thread(
                    background._looped_gradient_video,
                    img_path,
                    seg_path,
                    (end - start) / fps,
                    fps,
                    self.reel_width,
                    self.reel_height,
                )
                motion_path = background._apply_background_motion(
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
                    background._looped_image_video,
                    self.assets.bg_clip_path,
                    video_path,
                    total_seconds,
                    fps,
                    self.reel_width,
                    self.reel_height,
                )
                motion_path = background._apply_background_motion(
                    video_path, self.render_config.background_motion, fps
                )
                return [(motion_path, 0, segments[-1][2])]
            except (subprocess.CalledProcessError, OSError) as exc:
                log._log(f"   User background image unusable ({exc}), using gradient fallback")
        background.generate_background(img_path, self.reel_width, self.reel_height)
        await asyncio.to_thread(
            background._looped_gradient_video,
            img_path,
            fallback,
            total_seconds,
            fps,
            self.reel_width,
            self.reel_height,
        )
        motion_path = background._apply_background_motion(
            fallback, self.render_config.background_motion, fps
        )
        return [(motion_path, 0, segments[-1][2])]
