"""Daily Success Mindset — Short-form Reel Pipeline.

Orchestrates end-to-end reel creation: LLM script generation, TTS narration,
stock video sourcing, caption rendering, and ffmpeg compose render.
"""

import asyncio
import functools
import os

from lexigram.contracts.multimedia.types import MediaAsset

from shorts_creator.pipeline import bake, log

from . import narration, stock_video


class ReelAssetsMixin:
    """Mixin contributing reel pipeline methods for ReelPipeline."""

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
            log._log(f"   Beat analysis unavailable ({exc}), using plain music bed")

        if not beats:
            await asyncio.to_thread(
                bake._bake_music_bed,
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
            log._log(f"   Beat bake failed ({exc}), using plain music bed")
            await asyncio.to_thread(
                bake._bake_music_bed,
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
        log._log(f"   Synthesizing narration for {len(lines)} lines...")
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
