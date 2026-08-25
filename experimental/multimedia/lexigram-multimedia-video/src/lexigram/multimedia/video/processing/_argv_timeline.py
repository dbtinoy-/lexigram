"""ffmpeg argv builders for the timeline/transcode operation family.

Covers Trim, Crop, ChangeSpeed, Transcode, ExtractThumbnail, ToGif,
MuxAudio, and Concat. Pure functions: no subprocess execution or
filesystem I/O.
"""

from __future__ import annotations

from lexigram.contracts.multimedia.types import (
    ChangeSpeed,
    Concat,
    Crop,
    ExtractThumbnail,
    MuxAudio,
    ToGif,
    Transcode,
    Trim,
)
from lexigram.multimedia.video.processing._argv_shared import (
    ALLOWED_CODECS,
    RE_BITRATE,
    RE_CODEC,
    RE_RESOLUTION,
    assert_filter_field,
)

__all__ = [
    "build_change_speed_argv",
    "build_concat_argv",
    "build_crop_argv",
    "build_mux_audio_argv",
    "build_thumbnail_argv",
    "build_to_gif_argv",
    "build_transcode_argv",
    "build_trim_argv",
]


def build_trim_argv(
    operation: Trim,
    *,
    input_paths: list[str],
    output_path: str,
    ffmpeg_binary: str,
) -> list[str]:
    """Build argv for a :class:`Trim` operation (stream copy)."""
    return [
        ffmpeg_binary,
        "-y",
        "-ss",
        str(operation.start),
        "-to",
        str(operation.end),
        "-i",
        input_paths[0],
        "-c",
        "copy",
        output_path,
    ]


def build_crop_argv(
    operation: Crop,
    *,
    input_paths: list[str],
    output_path: str,
    ffmpeg_binary: str,
) -> list[str]:
    """Build argv for a :class:`Crop` operation."""
    return [
        ffmpeg_binary,
        "-y",
        "-i",
        input_paths[0],
        "-vf",
        f"crop={operation.width}:{operation.height}:{operation.x}:{operation.y}",
        output_path,
    ]


def build_change_speed_argv(
    operation: ChangeSpeed,
    *,
    input_paths: list[str],
    output_path: str,
    ffmpeg_binary: str,
) -> list[str]:
    """Build argv for a :class:`ChangeSpeed` operation (video + audio)."""
    factor = operation.factor
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


def build_transcode_argv(
    operation: Transcode,
    *,
    input_paths: list[str],
    output_path: str,
    ffmpeg_binary: str,
) -> list[str]:
    """Build argv for a :class:`Transcode` operation."""
    codec = operation.codec
    resolution = operation.resolution
    bitrate = operation.bitrate
    if codec:
        assert_filter_field("codec", codec, RE_CODEC, allowed=ALLOWED_CODECS)
    if resolution:
        assert_filter_field("resolution", resolution, RE_RESOLUTION)
    if bitrate:
        assert_filter_field("bitrate", bitrate, RE_BITRATE)
    argv = [ffmpeg_binary, "-y", "-i", input_paths[0]]
    if codec:
        argv += ["-c:v", codec]
    if resolution:
        argv += ["-s", resolution]
    if bitrate:
        argv += ["-b:v", bitrate]
    argv.append(output_path)
    return argv


def build_thumbnail_argv(
    operation: ExtractThumbnail,
    *,
    input_paths: list[str],
    output_path: str,
    ffmpeg_binary: str,
) -> list[str]:
    """Build argv for an :class:`ExtractThumbnail` operation."""
    return [
        ffmpeg_binary,
        "-y",
        "-ss",
        str(operation.timestamp),
        "-i",
        input_paths[0],
        "-frames:v",
        "1",
        output_path,
    ]


def build_to_gif_argv(
    operation: ToGif,
    *,
    input_paths: list[str],
    output_path: str,
    ffmpeg_binary: str,
) -> list[str]:
    """Build argv for a :class:`ToGif` operation."""
    argv = [ffmpeg_binary, "-y"]
    if operation.start is not None:
        argv += ["-ss", str(operation.start)]
    if operation.end is not None:
        argv += ["-to", str(operation.end)]
    argv += [
        "-i",
        input_paths[0],
        "-vf",
        f"fps={operation.fps},scale={operation.width}:-1:flags=lanczos",
        output_path,
    ]
    return argv


def build_mux_audio_argv(
    operation: MuxAudio,
    *,
    input_paths: list[str],
    output_path: str,
    ffmpeg_binary: str,
) -> list[str]:
    """Build argv for a :class:`MuxAudio` operation (replace or mix)."""
    if operation.mode == "replace":
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
    if operation.duck_under_existing:
        # sidechaincompress takes [signal-to-compress][sidechain-control] —
        # the music is the signal being ducked, controlled by the existing
        # (narration) track's level, then mixed with that same existing track.
        filter_complex = (
            f"[1:a]volume={operation.music_volume}[music];"
            "[music][0:a]sidechaincompress=threshold=0.05:ratio=8[ducked];"
            "[0:a][ducked]amix=inputs=2:duration=first[a]"
        )
    else:
        filter_complex = (
            f"[1:a]volume={operation.music_volume}[music];"
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


def build_concat_argv(
    operation: Concat,
    *,
    input_paths: list[str],
    output_path: str,
    ffmpeg_binary: str,
    clip_durations: list[float] | None = None,
) -> list[str]:
    """Build argv for a :class:`Concat` operation (plain or crossfade)."""
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
