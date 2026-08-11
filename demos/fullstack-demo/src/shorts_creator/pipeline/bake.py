"""Daily Success Mindset — Short-form Reel Pipeline.

Orchestrates end-to-end reel creation: LLM script generation, TTS narration,
stock video sourcing, caption rendering, and ffmpeg compose render.
"""

import os
import subprocess
import tempfile

from PIL import Image

from shorts_creator.pipeline.constants import (
    REEL_HEIGHT,
    REEL_WIDTH,
)
from shorts_creator.pipeline.render_config import RenderConfig


def _render_watermark_clip(
    watermark_path: str,
    out_path: str,
    total_frames: int,
    fps: float,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    render_config: RenderConfig | None = None,
) -> None:
    """Bake the watermark into a full-canvas transparent .mov: resized to a
    configurable percentage of the reel width, placed in a corner with a
    margin, alpha faded to a configurable opacity."""
    cfg = render_config or RenderConfig()
    img = Image.open(watermark_path).convert("RGBA")
    target_w = round(width * cfg.watermark_size_pct / 100)
    ratio = target_w / img.width
    img = img.resize((target_w, round(img.height * ratio)), Image.Resampling.LANCZOS)
    alpha = img.getchannel("A").point(lambda a: round(a * cfg.watermark_opacity))
    img.putalpha(alpha)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    margin = cfg.watermark_margin_px
    if cfg.watermark_corner == "bottom_left":
        pos = (margin, height - img.height - margin)
    elif cfg.watermark_corner == "top_right":
        pos = (width - img.width - margin, margin)
    elif cfg.watermark_corner == "top_left":
        pos = (margin, margin)
    else:
        pos = (width - img.width - margin, height - img.height - margin)
    canvas.paste(img, pos, img)
    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_path = os.path.join(tmp_dir, "wm.png")
        canvas.save(frame_path)
        list_path = os.path.join(tmp_dir, "concat.txt")
        duration = total_frames / fps
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


def _bake_music_bed(
    music_path: str, out_path: str, total_seconds: float, fade_seconds: float = 2.0
) -> None:
    """Loop the music bed to the narration length with a configurable
    fade in/out."""
    fade_out_start = max(0.0, total_seconds - fade_seconds)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            music_path,
            "-t",
            f"{total_seconds:.3f}",
            "-af",
            f"afade=t=in:d={fade_seconds},afade=t=out:st={fade_out_start:.3f}:d={fade_seconds}",
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            out_path,
        ],
        capture_output=True,
        check=True,
    )


def _loop_clip_to_duration(
    src_path: str,
    dst_path: str,
    total_seconds: float,
    fps: float,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
) -> None:
    """Loop a user clip (or trim it) so it covers exactly `total_seconds`,
    fitted (scaled+padded) onto the configured reel canvas."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            src_path,
            "-t",
            f"{total_seconds:.3f}",
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-r",
            str(fps),
            "-an",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            dst_path,
        ],
        capture_output=True,
        check=True,
    )
