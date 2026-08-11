from shorts_creator.pipeline import stock_video

"""Daily Success Mindset — Short-form Reel Pipeline.

Orchestrates end-to-end reel creation: LLM script generation, TTS narration,
stock video sourcing, caption rendering, and ffmpeg compose render.
"""

import os
import subprocess

from shorts_creator.pipeline.constants import (
    REEL_HEIGHT,
    REEL_WIDTH,
)
from shorts_creator.pipeline.log import _log


def generate_background(output_path: str, width: int = REEL_WIDTH, height: int = REEL_HEIGHT):
    subprocess.run(
        ["convert", "-size", f"{width}x{height}", "gradient:#0a0a32-#280f46", output_path],
        capture_output=True,
        check=True,
    )


def _looped_gradient_video(
    png_path: str,
    video_path: str,
    total_seconds: float,
    fps: float,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
) -> None:
    """Loop a static gradient image into an MP4 of `total_seconds` length.

    The stock-video fallback background: encoded at the project's own fps so
    the compose path can use the full clip without frame-rate surprises
    (ffmpeg's default fps of 25 would silently mismatch the 30fps project).
    """
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            png_path,
            "-t",
            str(total_seconds + 1),
            "-vf",
            f"scale={width}:{height}",
            "-r",
            str(fps),
            "-an",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "h264_nvenc",
            video_path,
        ],
        capture_output=True,
        check=True,
    )


def _looped_image_video(
    img_path: str,
    video_path: str,
    total_seconds: float,
    fps: float,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
) -> None:
    """Loop a still image into an MP4 of `total_seconds` length, cover-cropped
    onto the reel canvas so the frame is always full-bleed."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            img_path,
            "-t",
            str(total_seconds + 1),
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
            "-r",
            str(fps),
            "-an",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "h264_nvenc",
            video_path,
        ],
        capture_output=True,
        check=True,
    )


def _background_motion_vf(
    motion: str, fps: float, width: int = REEL_WIDTH, height: int = REEL_HEIGHT, frames: int = 2
) -> str:
    """Build the zoompan filter graph for a Ken Burns motion style. The input
    is upscaled 2x first so the zoompan crop lands on soft pixels, avoiding
    the sub-pixel jitter a 1:1 zoompan produces at reel resolutions."""
    if motion == "zoom":
        return (
            f"scale=iw*2:ih*2,zoompan=z='min(zoom+0.0004,1.15)':d=1:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps={fps}"
        )
    return (
        f"scale=iw*2:ih*2,zoompan=z=1.06:d=1:"
        f"x='(iw-iw/zoom)*on/{max(frames, 2)}':"
        f"y='ih/2-(ih/zoom/2)':s={width}x{height}:fps={fps}"
    )


def _apply_background_motion(path: str, motion: str, fps: float) -> str:
    """Re-encode a background clip with the configured Ken Burns motion;
    returns the original path when motion is off or the re-encode fails."""
    if motion == "none":
        return path
    frames = 2
    if motion == "pan":
        frames = max(round((stock_video._probe_duration(path) or 0.0) * fps), 2)
    out_path = os.path.splitext(path)[0] + "_motion.mp4"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                path,
                "-vf",
                _background_motion_vf(motion, fps, REEL_WIDTH, REEL_HEIGHT, frames),
                "-an",
                "-pix_fmt",
                "yuv420p",
                "-c:v",
                "libx264",
                out_path,
            ],
            capture_output=True,
            check=True,
        )
        return out_path
    except (subprocess.CalledProcessError, OSError) as exc:
        _log(f"   Background motion ({motion}) failed ({exc}), using original clip")
        return path


def _fit_clip_to_canvas(
    src_path: str, dst_path: str, fps: float, width: int = REEL_WIDTH, height: int = REEL_HEIGHT
) -> None:
    """Scale+pad a clip onto the configured reel canvas, preserving duration.

    Used for overlay layers (e.g. the outro asset) so a small/native-sized
    video fills the whole canvas instead of sitting at its raw size in the
    top-left corner of the overlay box.
    """
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            src_path,
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
