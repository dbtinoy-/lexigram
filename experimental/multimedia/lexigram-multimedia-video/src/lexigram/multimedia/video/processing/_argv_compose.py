"""ffmpeg argv builder for the ComposeVideo operation family.

Assembles the layered-composition filter graph (base + overlay layers +
audio layers with fades) for a :class:`ComposeVideo` operation. Pure
function: no subprocess execution or filesystem I/O.
"""

from __future__ import annotations

from lexigram.contracts.multimedia.types import ComposeVideo
from lexigram.multimedia.video.processing._argv_shared import (
    ALLOWED_CODECS,
    RE_BITRATE,
    RE_CODEC,
    RE_RESOLUTION,
    assert_filter_field,
)

__all__ = ["build_compose_argv"]


def build_compose_argv(
    operation: ComposeVideo,
    *,
    input_paths: list[str],
    output_path: str,
    ffmpeg_binary: str = "ffmpeg",
    base_duration: float | None = None,
    layer_durations: list[float] | None = None,
) -> list[str]:
    """Assemble the ffmpeg argv for a ComposeVideo operation.

    Input order: [0] base, [1..L] layer assets, [L+1..L+M] audio assets.
    Semantics per the ComposeVideo docstring: output duration == base
    duration; base audio dropped unless audio_layers present; layer fades
    are on the layer's own PTS (post setpts), the overlay enable window
    clips anything past `end`.

    Raises:
        ValueError: If fade_out/base_fade_out is set without base_duration,
            or a layer fade_out needs an end but no layer_durations entry.
    """
    # Fast path: nothing to do — plain copy.
    if (
        not operation.layers
        and not operation.audio_layers
        and operation.fade_in == 0.0
        and operation.fade_out == 0.0
        and operation.base_fade_out == 0.0
        and operation.encode is None
    ):
        return [ffmpeg_binary, "-y", "-i", input_paths[0], "-c", "copy", output_path]

    if operation.fade_out > 0 or operation.base_fade_out > 0:
        if base_duration is None:
            raise ValueError(
                "ComposeVideo fade_out/base_fade_out requires base_duration"
            )

    graph: list[str] = []
    prev = "[0:v]"
    if operation.base_fade_out > 0:
        assert base_duration is not None  # noqa: S101  # set when fade-out requested
        graph.append(
            f"[0:v]fade=t=out:st={base_duration - operation.base_fade_out}"
            f":d={operation.base_fade_out}[b0]"
        )
        prev = "[b0]"

    for j, layer in enumerate(operation.layers):
        i = j + 1
        # The overlay syncs its second input to the main clock by PTS, so the
        # layer's timeline must start AT its window start - otherwise the
        # frames before `start` are skipped when the enable window opens and
        # the last frame freezes on screen until the window closes.
        chain = f"[{i}:v]setpts=PTS-STARTPTS+{layer.start}/TB,format=yuva420p"
        if layer.end is not None:
            dur = layer.end - layer.start
        elif layer_durations is not None:
            dur = layer_durations[j]
        else:
            dur = None
        if layer.fade_in > 0:
            chain += f",fade=t=in:st={layer.start}:d={layer.fade_in}"
        if layer.fade_out > 0:
            if dur is None:
                raise ValueError(
                    "ComposeVideo layer fade_out requires end or layer_durations"
                )
            chain += (
                f",fade=t=out:st={layer.start + dur - layer.fade_out}"
                f":d={layer.fade_out}"
            )
        graph.append(f"{chain}[l{j}]")
        window = (
            f"gte(t,{layer.start})"
            if layer.end is None
            else f"between(t,{layer.start},{layer.end})"
        )
        graph.append(f"{prev}[l{j}]overlay=0:0:eof_action=pass:enable='{window}'[v{j}]")
        prev = f"[v{j}]"

    final = prev
    if operation.fade_in > 0 or operation.fade_out > 0:
        fades = []
        if operation.fade_in > 0:
            fades.append(f"fade=t=in:st=0:d={operation.fade_in}")
        if operation.fade_out > 0:
            assert base_duration is not None  # noqa: S101  # set when fade-out requested
            fades.append(
                f"fade=t=out:st={base_duration - operation.fade_out}"
                f":d={operation.fade_out}"
            )
        graph.append(f"{final}{','.join(fades)}[v]")
        final = "[v]"

    argv = [ffmpeg_binary, "-y"]
    argv += [arg for path in input_paths for arg in ("-i", path)]

    audio_labels: list[str] = []
    for m, audio in enumerate(operation.audio_layers):
        i = len(operation.layers) + 1 + m
        graph.append(
            f"[{i}:a]adelay={round(audio.start * 1000)}:all=1,volume={audio.volume}[a{m}]"
        )
        audio_labels.append(f"[a{m}]")
    if audio_labels:
        graph.append(
            f"{''.join(audio_labels)}amix=inputs={len(audio_labels)}"
            f":normalize=0:dropout_transition=0[a]"
        )

    argv += ["-filter_complex", ";".join(graph)]
    argv += ["-map", final]
    if audio_labels:
        argv += ["-map", "[a]"]
    if operation.encode is not None:
        encode = operation.encode
        assert_filter_field("codec", encode.codec, RE_CODEC, allowed=ALLOWED_CODECS)
        if encode.bitrate:
            assert_filter_field("bitrate", encode.bitrate, RE_BITRATE)
        if encode.resolution:
            assert_filter_field("resolution", encode.resolution, RE_RESOLUTION)
        argv += ["-c:v", encode.codec]
        if encode.bitrate:
            argv += ["-b:v", encode.bitrate]
        if encode.resolution:
            argv += ["-s", encode.resolution]
        if encode.fps:
            argv += ["-r", str(encode.fps)]
    if base_duration is not None:
        argv += ["-t", str(base_duration)]
    argv += ["-pix_fmt", "yuv420p", "-movflags", "+faststart", output_path]
    return argv
