"""Daily Success Mindset — Short-form Reel Pipeline.

Orchestrates end-to-end reel creation: LLM script generation, TTS narration,
stock video sourcing, caption rendering, and ffmpeg compose render.
"""

import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

from shorts_creator.pipeline.constants import (
    OUTRO_DEFAULT_SECONDS,
    REEL_HEIGHT,
    REEL_WIDTH,
)


def generate_outro_clip(
    output_path: str,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
    text: str = "Thanks for watching",
) -> None:
    """Generate the bundled default outro: a short gradient clip with
    subtle text, encoded at the reel's own fps so the compose path can use
    the full clip without frame-rate surprises.
    """
    img = Image.new("RGB", (width, height), (10, 10, 50))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width, height), fill=(10, 10, 50))
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 96)
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text(
        ((width - (bbox[2] - bbox[0])) / 2, (height - (bbox[3] - bbox[1])) / 2),
        text,
        font=font,
        fill=(255, 255, 255, 255),
    )
    frame_path = output_path + ".png"
    img.save(frame_path)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            frame_path,
            "-t",
            str(OUTRO_DEFAULT_SECONDS),
            "-vf",
            f"scale={width}:{height}",
            "-r",
            "30",
            "-an",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "h264_nvenc",
            output_path,
        ],
        capture_output=True,
        check=True,
    )
    os.unlink(frame_path)


_OUTRO_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _fit_outro_text(
    text: str,
    canvas_width: int,
    max_px: int = 96,
    min_px: int = 24,
):
    """Fit outro text to the canvas: shrink from ``max_px`` down to ``min_px``
    while the line is wider than 85% of the canvas, then word-wrap on spaces
    so every line fits. Returns ``(font, lines)`` for the clip builder."""
    probe = ImageDraw.Draw(Image.new("RGBA", (canvas_width, 16)))
    limit = int(canvas_width * 0.85)

    def shrink():
        px = max_px
        while px >= min_px:
            font = ImageFont.truetype(_OUTRO_FONT_PATH, px)
            bbox = probe.textbbox((0, 0), text, font=font)
            if bbox[2] - bbox[0] <= limit:
                return font, [text]
            px -= 4
        return None

    fitted = shrink()
    if fitted is not None:
        return fitted

    font = ImageFont.truetype(_OUTRO_FONT_PATH, min_px)
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = (current + " " + word).strip()
        bbox = probe.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= limit or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return font, lines


def _render_outro_text_clip(
    text: str,
    out_path: str,
    outro_seconds: float,
    fps: float,
    width: int = REEL_WIDTH,
    height: int = REEL_HEIGHT,
) -> None:
    """Render `text` centered on a transparent full-canvas clip the length
    of the outro window (qtrle, like the watermark overlay)."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font, lines = _fit_outro_text(text, width)
    line_h = font.size + 12
    block_h = len(lines) * line_h
    y0 = (height - block_h) / 2
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (width - (bbox[2] - bbox[0])) / 2
        y = y0 + i * line_h - bbox[1]
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_path = os.path.join(tmp_dir, "outro_text.png")
        img.save(frame_path)
        list_path = os.path.join(tmp_dir, "concat.txt")
        duration = outro_seconds
        with open(list_path, "w") as f:
            f.write(f"file '{frame_path}'\nduration {duration + 0.5:.3f}\n")
            f.write(f"file '{frame_path}'\n")
        subprocess.run(
            [
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
            ],
            capture_output=True,
            check=True,
        )
