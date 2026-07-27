"""Compose plan builder (design spec §5).

Pure module: `build_compose_plan(...) -> ComposePlan` with no I/O. Timing
math stays consistent with `ReelPipeline._run_ffmpeg`'s bake loop so word
and chunk timing cannot drift between the plan and the caption clips.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from lexigram.contracts.multimedia.types import (
    ComposeAudioLayer,
    ComposeLayer,
    EncodeSpec,
    MediaAsset,
)

from shorts_creator.pipeline import captions
from shorts_creator.pipeline.pipeline import (
    FADE_IN_SECONDS,
    REEL_HEIGHT,
    REEL_WIDTH,
    held_line_frames,
)
from shorts_creator.pipeline.render_config import RenderConfig

if TYPE_CHECKING:
    from shorts_creator.pipeline.script_parser import ParsedScript


@dataclass(frozen=True)
class ComposePlan:
    base_asset: MediaAsset
    overlays: list[ComposeLayer]
    audio_layers: list[ComposeAudioLayer]
    fade_in: float
    fade_out: float
    encode: EncodeSpec
    total_frames: int
    narration_end_frames: int


def _local_asset(mime_type: str, path: str) -> MediaAsset:
    return MediaAsset(mime_type=mime_type, provider="local-http", uri=f"file://{path}")


def _line_text(script: ParsedScript, idx: int) -> str:
    all_lines = (
        [script.hook]
        + list(script.top_items)
        + list(script.message_lines)
        + [script.metaphor, script.conclusion]
    )
    return all_lines[idx]


def _fallback_chunks(words: list[dict]) -> list[list[dict]]:
    sizes = captions._fallback_sizes(words, captions.FALLBACK_TARGET_SIZE)
    return captions._sizes_to_chunks(words, sizes)


def caption_chunk_windows(
    chunks: list[list[dict]],
    words: list[dict],
    fps: float,
    per_line_frames: int,
) -> list[tuple[list[dict], int, int]]:
    """Compute (chunk, start_frame, end_frame) windows for caption chunks.

    Mirrors the math in `ReelPipeline._run_ffmpeg`: per-word frame starts from
    Whisper timings, chunk start = start of the chunk's first word, chunk end
    = start of the next chunk (or the line end).
    """
    starts = [max(0, min(round(w["start"] * fps), per_line_frames - 1)) for w in words]
    starts[0] = 0
    chunk_starts: list[int] = []
    consumed = 0
    for chunk in chunks:
        chunk_starts.append(starts[consumed])
        consumed += len(chunk)
    chunk_ends = chunk_starts[1:] + [per_line_frames]
    chunk_ends = [max(end, start + 1) for start, end in zip(chunk_starts, chunk_ends)]
    return list(zip(chunks, chunk_starts, chunk_ends))


def chunk_word_frames(
    chunk: list[dict],
    seg_start_rel: int,
    seg_end_rel: int,
    fps: float,
    per_line_frames: int,
) -> list[int]:
    """Per-word frame counts within a caption chunk (word-by-word highlight).

    Mirrors the math in `ReelPipeline._run_ffmpeg` (lines 865-871): word frame
    boundaries derived from the same Whisper timings used for chunk windows.
    Every non-last word hands off at the next word's spoken start; the last
    word holds only until its own spoken end (never past the chunk window),
    so the highlight does not linger on the final word once the audio has
    moved on.
    """
    word_starts_abs = [max(0, min(round(w["start"] * fps), per_line_frames - 1)) for w in chunk]
    word_starts_abs[0] = seg_start_rel
    word_starts_rel = [s - seg_start_rel for s in word_starts_abs]
    last_end_rel = min(
        seg_end_rel - seg_start_rel,
        max(0, round(chunk[-1]["end"] * fps)) - seg_start_rel,
    )
    word_ends_rel = word_starts_rel[1:] + [last_end_rel]
    return [max(1, e - s) for s, e in zip(word_starts_rel, word_ends_rel)]


def hook_font_size(
    texts: list[str],
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    render_config: RenderConfig | None = None,
) -> int:
    """Fit the hook screen font size to the block (spec §4, mirrors
    `ReelPipeline._run_ffmpeg` lines 812-820)."""
    cfg = render_config or RenderConfig()
    max_chars = max(len(t) for t in texts)
    available_width_px = cfg.hook_block_width_pct / 100 * width
    width_fit_size = available_width_px / (max_chars * cfg.hook_char_width_factor)
    max_block_height_px = cfg.hook_block_height_pct / 100 * height
    height_fit_size = max_block_height_px / (len(texts) * cfg.hook_line_height_factor)
    return round(
        max(cfg.hook_min_font_size, min(cfg.hook_max_font_size, width_fit_size, height_fit_size))
    )


def build_compose_plan(
    script: ParsedScript,
    line_data: list[tuple[str, float, list[dict]]],
    bg_path: str,
    fps: float,
    temp_dir: str = "",
    bg_segments: list[tuple[str, int, int]] | None = None,
    caption_groups_by_idx: dict[int, list[list[dict]]] | None = None,
    caption_styles: list[str] | None = None,
    caption_style: str = "highlight",
    outro_path: str = "",
    outro_seconds: float = 0.0,
    outro_text_path: str = "",
    watermark_path: str = "",
    music_bed_path: str = "",
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    render_config: RenderConfig | None = None,
    stages: dict | None = None,
) -> ComposePlan:
    """Build the ComposePlan for a scripted reel (spec §5).

    Args:
        script: Parsed script (hook / message lines / metaphor / conclusion).
        line_data: (wav_path, duration_seconds, words) per narration line.
        bg_path: Path to the background footage video (used when
            ``bg_segments`` is None).
        fps: Timeline frames per second.
        temp_dir: Directory holding the baked hook/caption/watermark/music
            movs and the black base clip. Empty string keeps asset uris relative.
        bg_segments: (path, start_frame, end_frame) background clips per
            narrative segment. When given, one overlay is emitted per
            segment instead of the single full-length ``bg_path`` window;
            an empty list emits no background overlays.
        caption_groups_by_idx: Pre-grouped caption chunks per line index
            (from `captions.group_by_thought`). Lines missing an entry fall
            back to the pure deterministic grouping.
        caption_styles: Caption styles of the resolved format. When empty
            the format is style-less: if the script carries top_items (topn)
            the hook screen keeps its overlay and each top item gets one
            numbered ranked screen (rank_<idx>.mov); without top_items the
            render is full-bleed background plus narration and music.
            Defaults to ["highlight"].
        caption_style: Resolved caption style of the profile. "list" swaps
            the per-item ranked screens for a single full-list screen
            (list.mov) spanning the whole top_items segment.
        outro_path: Video file played once narration ends (its natural
            duration; no lead-in, no hold seconds).
        outro_seconds: Probed duration of the outro clip.
        outro_text_path: Transparent quicktime (video/quicktime) text overlay spanning the outro window; empty string skips the overlay.
        watermark_path: Baked full-canvas transparent watermark .mov.
        music_bed_path: Baked music bed .wav (already faded + looped to the
            narration length).
        width: Reel canvas width in px; drives layout math and the encode.
        height: Reel canvas height in px.
        render_config: Overrides for caption chunking and font-fit math
            (defaults to RenderConfig()).
        stages: Pipeline stage toggles (`background`, `music`, `outro`,
            `watermark`). When a stage is `False` its overlay is skipped;
            `outro` only swaps the clip path upstream (never removes the
            segment, per spec). Defaults to all stages on.

    Returns:
        ComposePlan with frame-aligned overlay/audio windows.
    """
    styles = caption_styles if caption_styles is not None else ["highlight"]
    if caption_style not in (None, "", "highlight", "list"):
        caption_style = "highlight"
    cfg = render_config or RenderConfig()
    stages = stages or {}
    line_frames = held_line_frames(
        line_data,
        fps,
        cfg.section_holds or {},
        getattr(script, "section_names", []),
    )
    position = sum(line_frames)
    outro_frames = round(outro_seconds * fps)
    total_frames = position + outro_frames

    def rel(path: str) -> str:
        return os.path.join(temp_dir, path) if temp_dir else path

    overlays: list[ComposeLayer] = []
    if stages.get("background") is not False:
        if bg_segments is not None:
            for path, start_frame, end_frame in bg_segments:
                overlays.append(
                    ComposeLayer(
                        asset=_local_asset("video/mp4", path),
                        start=start_frame / fps,
                        end=end_frame / fps,
                    )
                )
        else:
            overlays.append(
                ComposeLayer(
                    asset=_local_asset("video/mp4", bg_path),
                    start=0.0,
                    end=position / fps,
                )
            )
    cursor = 0
    for idx, (wav_path, duration, words) in enumerate(line_data):
        per_line_frames = line_frames[idx]
        if not words:
            words = [{"word": _line_text(script, idx), "start": 0.0, "end": duration}]
        if not styles:
            if script.top_items:
                if idx == 0:
                    overlays.append(
                        ComposeLayer(
                            asset=_local_asset("video/quicktime", rel("hook.mov")),
                            start=0.0,
                            end=per_line_frames / fps,
                        )
                    )
                elif caption_style == "list":
                    if idx == 1:
                        items_n = min(len(script.top_items), len(line_data) - 1)
                        seg_frames = sum(line_frames[1 : items_n + 1])
                        if seg_frames > 0:
                            overlays.append(
                                ComposeLayer(
                                    asset=_local_asset("video/quicktime", rel("list.mov")),
                                    start=cursor / fps,
                                    end=(cursor + seg_frames) / fps,
                                )
                            )
                elif idx <= len(script.top_items):
                    overlays.append(
                        ComposeLayer(
                            asset=_local_asset("video/quicktime", rel(f"rank_{idx}.mov")),
                            start=cursor / fps,
                            end=(cursor + per_line_frames) / fps,
                        )
                    )
            cursor += per_line_frames
            continue
        if idx == 0:
            overlays.append(
                ComposeLayer(
                    asset=_local_asset("video/quicktime", rel("hook.mov")),
                    start=0.0,
                    end=per_line_frames / fps,
                )
            )
        else:
            groups = (caption_groups_by_idx or {}).get(idx)
            if groups is None:
                groups = _fallback_chunks(words)
            chunks = [
                chunk[i : i + cfg.caption_max_words]
                for chunk in groups
                for i in range(0, len(chunk), cfg.caption_max_words)
            ]
            windows = caption_chunk_windows(chunks, words, fps, per_line_frames)
            for chunk_idx, (chunk, seg_start_rel, seg_end_rel) in enumerate(windows):
                overlays.append(
                    ComposeLayer(
                        asset=_local_asset(
                            "video/quicktime", rel(f"caption_{idx}_{chunk_idx}.mov")
                        ),
                        start=(cursor + seg_start_rel) / fps,
                        end=(cursor + seg_end_rel) / fps,
                    )
                )
        cursor += per_line_frames

    if outro_path:
        overlays.append(
            ComposeLayer(
                asset=_local_asset("video/mp4", outro_path),
                start=position / fps,
                end=total_frames / fps,
            )
        )
    if outro_text_path:
        overlays.append(
            ComposeLayer(
                asset=_local_asset("video/quicktime", outro_text_path),
                start=position / fps,
                end=total_frames / fps,
            )
        )
    if watermark_path and stages.get("watermark") is not False:
        overlays.append(
            ComposeLayer(
                asset=_local_asset("video/quicktime", rel("watermark.mov")),
                start=0.0,
                end=total_frames / fps,
            )
        )

    audio_layers = [
        ComposeAudioLayer(
            asset=_local_asset("audio/wav", wav_path),
            start=sum(line_frames[:i]) / fps,
            volume=1.0,
        )
        for i, (wav_path, _, _) in enumerate(line_data)
    ]
    if music_bed_path:
        audio_layers.append(
            ComposeAudioLayer(
                asset=_local_asset("audio/wav", rel("music_bed.wav")),
                start=0.0,
                volume=cfg.music_volume,
            )
        )

    return ComposePlan(
        base_asset=_local_asset("video/mp4", rel("black_base.mp4")),
        overlays=overlays,
        audio_layers=audio_layers,
        fade_in=FADE_IN_SECONDS,
        fade_out=cfg.fade_out_seconds,
        encode=EncodeSpec(
            codec="hevc_nvenc", bitrate="10M", resolution=f"{width}x{height}", fps=round(fps)
        ),
        total_frames=total_frames,
        narration_end_frames=position,
    )
