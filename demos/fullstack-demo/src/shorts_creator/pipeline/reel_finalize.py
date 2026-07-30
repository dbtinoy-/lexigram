"""Daily Success Mindset — Short-form Reel Pipeline.

Orchestrates end-to-end reel creation: LLM script generation, TTS narration,
stock video sourcing, caption rendering, and ffmpeg compose render.
"""

import asyncio
import os
import subprocess

from shorts_creator.pipeline import log


class ReelFinalizeMixin:
    """Mixin contributing reel pipeline methods for ReelPipeline."""

    def _write_recipe(self, path: str, params: dict) -> None:
        import json as _json

        with open(path, "w") as f:
            _json.dump(params, f, indent=2)

    def _write_render_output(self, path: str, data: bytes) -> None:
        with open(path, "wb") as fh:
            fh.write(data)

    def _make_black_base(self, path: str, total_frames: int, fps: float) -> None:
        """Encode a full-length black video clip (design §5.3) via ffmpeg."""
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=black:size={self.reel_width}x{self.reel_height}:rate={fps}",
                "-t",
                str(total_frames / fps),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                path,
            ],
            capture_output=True,
            check=True,
        )

    async def _loudnorm_output(self) -> None:
        """Remux the master with Loudness-normalized AAC audio."""
        probe = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            self.output,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await probe.communicate()
        if probe.returncode != 0 or b"audio" not in stdout:
            log._log("   No audio stream; skipping loudnorm pass")
            return
        tmp = f"{self.output}.loudnorm.mp4"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            self.output,
            "-c:v",
            "copy",
            "-af",
            f"loudnorm=I={self.render_config.loudness_target_lufs}:TP=-1.5:LRA=11",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            tmp,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        if proc.returncode == 0 and os.path.exists(tmp):
            os.replace(tmp, self.output)
            log._log(f"   Loudness normalized to {self.render_config.loudness_target_lufs} LUFS")
        else:
            log._log("   Loudnorm pass failed; keeping original audio")

    def _transcode_720p(self):
        """Write a 720px-wide H.264 companion next to the master file - FB
        Reels loads faster with a smaller H.264 file than the HEVC master.
        Aspect ratio follows the configured reel canvas (720x1280 for the
        default 1080x1920).
        """
        out_720 = self.output.replace(".mp4", "_720p.mp4")
        cmd = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            self.output,
            "-vf",
            "scale=min(720\\,iw):-2",
            "-c:v",
            "h264_nvenc",
            "-b:v",
            "2.5M",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            out_720,
        ]
        try:
            subprocess.run(cmd, check=True, timeout=180)
            log._log(f"   720p variant: {out_720}")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
            log._log(f"   720p transcode failed: {exc}")

    def _extract_screenshots(self, count: int = 3):
        """Grab `count` evenly-spaced JPEG stills from the finished render
        into run_dir, so the output folder has a quick visual preview
        without opening the video."""
        run_dir = getattr(self, "run_dir", None) or os.path.dirname(self.output)
        if not os.path.exists(self.output):
            return
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                self.output,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        duration = float(probe.stdout.strip())
        for i in range(count):
            timestamp = duration * (i + 1) / (count + 1)
            shot_path = os.path.join(run_dir, f"screenshot_{i + 1}.jpg")
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    str(timestamp),
                    "-i",
                    self.output,
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
                    shot_path,
                ],
                capture_output=True,
                check=True,
            )
        log._log(f"   Screenshots saved to {run_dir}/")
