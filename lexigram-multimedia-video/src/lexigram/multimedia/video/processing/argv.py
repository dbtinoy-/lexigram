"""Pure ffmpeg argv builders — one function per VideoOperation variant.

No subprocess execution or filesystem I/O here; these functions only
assemble command-line argument lists so they're trivially unit-testable.
"""

from __future__ import annotations

from lexigram.contracts.multimedia.types import (
    BurnSubtitles,
    ChangeSpeed,
    ColorFilter,
    Concat,
    Crop,
    ExtractThumbnail,
    MuxAudio,
    OverlayImage,
    OverlayText,
    RawFilter,
    ToGif,
    Transcode,
    Trim,
    VideoOperation,
)

_COLOR_PRESETS = {
    "grayscale": "hue=s=0",
    "sepia": (
        "colorchannelmixer=0.393:0.769:0.189:0:0.349:0.686:0.168:0:0.272:0.534:0.131"
    ),
    "vintage": "curves=vintage,vignette",
}

_POSITION_EXPR = {
    "top": "(w-text_w)/2:20",
    "bottom": "(w-text_w)/2:h-text_h-20",
    "center": "(w-text_w)/2:(h-text_h)/2",
    "top-left": "20:20",
    "top-right": "w-text_w-20:20",
    "bottom-left": "20:h-text_h-20",
    "bottom-right": "w-text_w-20:h-text_h-20",
}

_OVERLAY_POSITION_EXPR = {
    "top": "(W-w)/2:20",
    "bottom": "(W-w)/2:H-h-20",
    "center": "(W-w)/2:(H-h)/2",
    "top-left": "20:20",
    "top-right": "W-w-20:20",
    "bottom-left": "20:H-h-20",
    "bottom-right": "W-w-20:H-h-20",
}


def build_argv(
    operation: VideoOperation,
    *,
    input_paths: list[str],
    output_path: str,
    ffmpeg_binary: str = "ffmpeg",
    clip_durations: list[float] | None = None,
    subtitle_path: str | None = None,
) -> list[str]:
    match operation:
        case Trim(start=start, end=end):
            return [
                ffmpeg_binary,
                "-y",
                "-ss",
                str(start),
                "-to",
                str(end),
                "-i",
                input_paths[0],
                "-c",
                "copy",
                output_path,
            ]
        case Crop(x=x, y=y, width=width, height=height):
            return [
                ffmpeg_binary,
                "-y",
                "-i",
                input_paths[0],
                "-vf",
                f"crop={width}:{height}:{x}:{y}",
                output_path,
            ]
        case ChangeSpeed(factor=factor):
            return [
                ffmpeg_binary,
                "-y",
                "-i",
                input_paths[0],
                "-filter_complex",
                f"[0:v]setpts={1.0 / factor}*PTS[v];[0:a]atempo={factor}[a]",
                "-map",
                "[v]",
                "-map",
                "[a]",
                output_path,
            ]
        case ColorFilter(
            preset=preset,
            brightness=brightness,
            contrast=contrast,
            saturation=saturation,
        ):
            if preset and preset != "none":
                vf = _COLOR_PRESETS[preset]
            else:
                vf = f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}"
            return [ffmpeg_binary, "-y", "-i", input_paths[0], "-vf", vf, output_path]
        case Transcode(codec=codec, resolution=resolution, bitrate=bitrate):
            argv = [ffmpeg_binary, "-y", "-i", input_paths[0]]
            if codec:
                argv += ["-c:v", codec]
            if resolution:
                argv += ["-s", resolution]
            if bitrate:
                argv += ["-b:v", bitrate]
            argv.append(output_path)
            return argv
        case ExtractThumbnail(timestamp=timestamp):
            return [
                ffmpeg_binary,
                "-y",
                "-ss",
                str(timestamp),
                "-i",
                input_paths[0],
                "-frames:v",
                "1",
                output_path,
            ]
        case ToGif(start=start, end=end, fps=fps, width=width):
            argv = [ffmpeg_binary, "-y"]
            if start is not None:
                argv += ["-ss", str(start)]
            if end is not None:
                argv += ["-to", str(end)]
            argv += [
                "-i",
                input_paths[0],
                "-vf",
                f"fps={fps},scale={width}:-1:flags=lanczos",
                output_path,
            ]
            return argv
        case OverlayText(
            text=text,
            position=position,
            font_size=font_size,
            color=color,
            start=start,
            end=end,
        ):
            xy = _POSITION_EXPR[position]
            drawtext = (
                f"drawtext=text='{_escape_drawtext(text)}':fontsize={font_size}"
                f":fontcolor={color}:x={xy.split(':')[0]}:y={xy.split(':')[1]}"
            )
            if start is not None and end is not None:
                drawtext += f":enable='between(t,{start},{end})'"
            return [
                ffmpeg_binary,
                "-y",
                "-i",
                input_paths[0],
                "-vf",
                drawtext,
                output_path,
            ]
        case OverlayImage(position=position, opacity=opacity, start=start, end=end):
            xy = _OVERLAY_POSITION_EXPR[position]
            filters = []
            if opacity < 1.0:
                filters.append(f"[1:v]colorchannelmixer=aa={opacity}[ovl]")
                overlay_input = "[ovl]"
            else:
                overlay_input = "[1:v]"
            overlay_expr = f"[0:v]{overlay_input}overlay={xy}"
            if start is not None and end is not None:
                overlay_expr += f":enable='between(t,{start},{end})'"
            filters.append(overlay_expr + "[v]")
            return [
                ffmpeg_binary,
                "-y",
                "-i",
                input_paths[0],
                "-i",
                input_paths[1],
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[v]",
                "-map",
                "0:a?",
                output_path,
            ]
        case BurnSubtitles():
            return [
                ffmpeg_binary,
                "-y",
                "-i",
                input_paths[0],
                "-vf",
                f"subtitles={subtitle_path}",
                output_path,
            ]
        case MuxAudio(mode=mode, music_volume=music_volume, duck_under_existing=duck):
            if mode == "replace":
                return [
                    ffmpeg_binary,
                    "-y",
                    "-i",
                    input_paths[0],
                    "-i",
                    input_paths[1],
                    "-map",
                    "0:v",
                    "-map",
                    "1:a",
                    "-c:v",
                    "copy",
                    "-shortest",
                    output_path,
                ]
            # mode == "mix"
            if duck:
                # sidechaincompress takes [signal-to-compress][sidechain-control] —
                # the music is the signal being ducked, controlled by the existing
                # (narration) track's level, then mixed with that same existing track.
                filter_complex = (
                    f"[1:a]volume={music_volume}[music];"
                    "[music][0:a]sidechaincompress=threshold=0.05:ratio=8[ducked];"
                    "[0:a][ducked]amix=inputs=2:duration=first[a]"
                )
            else:
                filter_complex = (
                    f"[1:a]volume={music_volume}[music];"
                    "[0:a][music]amix=inputs=2:duration=first[a]"
                )
            return [
                ffmpeg_binary,
                "-y",
                "-i",
                input_paths[0],
                "-i",
                input_paths[1],
                "-filter_complex",
                filter_complex,
                "-map",
                "0:v",
                "-map",
                "[a]",
                output_path,
            ]
        case Concat():
            return _build_concat_argv(
                operation,
                input_paths=input_paths,
                output_path=output_path,
                ffmpeg_binary=ffmpeg_binary,
                clip_durations=clip_durations,
            )
        case RawFilter(filter_complex=filter_complex, maps=maps, extra_args=extra_args):
            argv = [ffmpeg_binary, "-y"]
            for path in input_paths:
                argv += ["-i", path]
            argv += ["-filter_complex", filter_complex]
            for m in maps:
                argv += ["-map", m]
            argv += extra_args
            argv.append(output_path)
            return argv
    raise TypeError(f"unsupported operation: {operation!r}")


def _build_concat_argv(
    operation: Concat,
    *,
    input_paths: list[str],
    output_path: str,
    ffmpeg_binary: str,
    clip_durations: list[float] | None,
) -> list[str]:
    transitions = operation.transitions
    has_crossfade = transitions is not None and any(
        t.kind == "crossfade" for t in transitions
    )

    if not has_crossfade:
        argv = [ffmpeg_binary, "-y"]
        for path in input_paths:
            argv += ["-i", path]
        n = len(input_paths)
        filter_complex = (
            "".join(f"[{i}:v][{i}:a]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]"
        )
        argv += [
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
            output_path,
        ]
        return argv

    if clip_durations is None:
        raise ValueError("clip_durations is required for crossfade concat")

    argv = [ffmpeg_binary, "-y"]
    for path in input_paths:
        argv += ["-i", path]

    filters = []
    cumulative = clip_durations[0]
    prev_v, prev_a = "0:v", "0:a"
    for i in range(1, len(input_paths)):
        spec = transitions[i - 1] if transitions and i - 1 < len(transitions) else None
        # Only "crossfade" pairs actually blend; a "cut" (or missing spec) uses
        # a minimal-duration xfade — an almost-instantaneous switch at `offset`
        # rather than a blend — i.e. a hard cut expressed in the same xfade/
        # acrossfade filter chain the other pairs already use. This keeps every
        # pair in one sequential filter graph instead of mixing the `concat`
        # filter and `xfade` filter within a single operation.
        #
        # NOTE: this must NOT be exactly 0.0. Verified against real ffmpeg
        # (6.1.1): when `offset` lands exactly at the end of the preceding
        # segment (which is what `offset = cumulative - duration` produces
        # when duration is 0), ffmpeg's xfade/acrossfade filters silently
        # truncate the rest of the chain instead of erroring — the output
        # drops almost the entire following clip. A small positive epsilon
        # keeps `offset` strictly below `cumulative` and avoids that dead
        # zone while still reading as an instant cut.
        _CUT_DURATION = 1 / 30
        duration = spec.duration if spec and spec.kind == "crossfade" else _CUT_DURATION
        offset = cumulative - duration
        out_v, out_a = f"v{i}", f"a{i}"
        filters.append(
            f"[{prev_v}][{i}:v]xfade=transition=fade:duration={duration}:offset={offset}[{out_v}]"
        )
        filters.append(f"[{prev_a}][{i}:a]acrossfade=d={duration}[{out_a}]")
        prev_v, prev_a = out_v, out_a
        cumulative += clip_durations[i] - duration

    argv += [
        "-filter_complex",
        ";".join(filters),
        "-map",
        f"[{prev_v}]",
        "-map",
        f"[{prev_a}]",
        output_path,
    ]
    return argv


def _escape_drawtext(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def cues_to_srt(cues: list) -> str:
    def fmt(t: float) -> str:
        hours, rem = divmod(t, 3600)
        minutes, seconds = divmod(rem, 60)
        millis = round((seconds - int(seconds)) * 1000)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{millis:03d}"

    lines = []
    for i, cue in enumerate(cues, start=1):
        lines.append(str(i))
        lines.append(f"{fmt(cue.start)} --> {fmt(cue.end)}")
        lines.append(cue.text)
        lines.append("")
    return "\n".join(lines)


__all__ = ["build_argv", "cues_to_srt"]
