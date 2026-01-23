import pytest

from lexigram.contracts.multimedia.types import (
    ComposeAudioLayer,
    ComposeLayer,
    ComposeVideo,
    EncodeSpec,
    MediaAsset,
)
from lexigram.multimedia.video.processing.argv import build_compose_argv


def _base() -> MediaAsset:
    return MediaAsset(mime_type="video/mp4", provider="test", uri="base.mp4")


def _layer(start=1.0, end=None, fade_in=0.0, fade_out=0.0) -> ComposeLayer:
    return ComposeLayer(
        asset=MediaAsset(
            mime_type="video/quicktime", provider="test", uri="layer.mov"
        ),
        start=start,
        end=end,
        fade_in=fade_in,
        fade_out=fade_out,
    )


def _pairs(argv: list[str]) -> list[tuple[str, str]]:
    return list(zip(argv, argv[1:]))


def _fc(argv: list[str]) -> str:
    return argv[argv.index("-filter_complex") + 1]


def test_single_layer_basic():
    op = ComposeVideo(asset=_base(), layers=[_layer()])
    argv = build_compose_argv(
        op, input_paths=["base.mp4", "layer.mov"], output_path="out.mp4"
    )
    assert argv == [
        "ffmpeg",
        "-y",
        "-i",
        "base.mp4",
        "-i",
        "layer.mov",
        "-filter_complex",
        "[1:v]setpts=PTS-STARTPTS,format=auto[l0];"
        "[0:v][l0]overlay=0:0:enable='gte(t,1.0)'[v0]",
        "-map",
        "[v0]",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "out.mp4",
    ]


def test_two_layers_windows():
    op = ComposeVideo(asset=_base(), layers=[_layer(start=1.0), _layer(start=2.0, end=4.0)])
    argv = build_compose_argv(
        op, input_paths=["base.mp4", "l1.mov", "l2.mov"], output_path="out.mp4"
    )
    assert argv == [
        "ffmpeg",
        "-y",
        "-i",
        "base.mp4",
        "-i",
        "l1.mov",
        "-i",
        "l2.mov",
        "-filter_complex",
        "[1:v]setpts=PTS-STARTPTS,format=auto[l0];"
        "[0:v][l0]overlay=0:0:enable='gte(t,1.0)'[v0];"
        "[2:v]setpts=PTS-STARTPTS,format=auto[l1];"
        "[v0][l1]overlay=0:0:enable='between(t,2.0,4.0)'[v1]",
        "-map",
        "[v1]",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "out.mp4",
    ]


def test_layer_fades_with_end_set():
    op = ComposeVideo(
        asset=_base(), layers=[_layer(start=1.0, end=4.0, fade_in=0.2, fade_out=0.3)]
    )
    argv = build_compose_argv(
        op, input_paths=["base.mp4", "layer.mov"], output_path="out.mp4"
    )
    assert (
        "[1:v]setpts=PTS-STARTPTS,format=auto,fade=t=in:st=0:d=0.2,"
        "fade=t=out:st=2.7:d=0.3[l0]" in _fc(argv)
    )


def test_layer_fade_out_with_probed_duration():
    op = ComposeVideo(asset=_base(), layers=[_layer(start=1.0, fade_out=0.3)])
    argv = build_compose_argv(
        op,
        input_paths=["base.mp4", "layer.mov"],
        output_path="out.mp4",
        layer_durations=[3.0],
    )
    assert "fade=t=out:st=2.7:d=0.3[l0]" in _fc(argv)


def test_layer_fade_out_probed_missing_raises():
    op = ComposeVideo(asset=_base(), layers=[_layer(start=1.0, fade_out=0.3)])
    with pytest.raises(ValueError):
        build_compose_argv(
            op, input_paths=["base.mp4", "layer.mov"], output_path="out.mp4"
        )


def test_global_fades_need_base_duration():
    op = ComposeVideo(asset=_base(), fade_out=0.5)
    with pytest.raises(ValueError):
        build_compose_argv(op, input_paths=["base.mp4"], output_path="out.mp4")
    op = ComposeVideo(asset=_base(), base_fade_out=0.75)
    with pytest.raises(ValueError):
        build_compose_argv(op, input_paths=["base.mp4"], output_path="out.mp4")


def test_global_and_base_fades():
    op = ComposeVideo(
        asset=_base(),
        layers=[_layer()],
        fade_in=0.5,
        fade_out=0.5,
        base_fade_out=0.75,
    )
    argv = build_compose_argv(
        op,
        input_paths=["base.mp4", "layer.mov"],
        output_path="out.mp4",
        base_duration=30.0,
    )
    assert "[0:v]fade=t=out:st=29.25:d=0.75[b0]" in _fc(argv)
    assert "[b0][l0]overlay=0:0:enable='gte(t,1.0)'[v0]" in _fc(argv)
    assert "[v0]fade=t=in:st=0:d=0.5,fade=t=out:st=29.5:d=0.5[v]" in _fc(argv)
    assert ("-map", "[v]") in _pairs(argv)


def test_audio_layers_amix():
    op = ComposeVideo(
        asset=_base(),
        audio_layers=[
            ComposeAudioLayer(
                asset=MediaAsset(mime_type="audio/wav", provider="test", uri="n1.wav"),
                start=5.0,
            ),
            ComposeAudioLayer(
                asset=MediaAsset(mime_type="audio/wav", provider="test", uri="n2.wav"),
                start=7.5,
                volume=0.8,
            ),
        ],
    )
    argv = build_compose_argv(
        op, input_paths=["base.mp4", "n1.wav", "n2.wav"], output_path="out.mp4"
    )
    assert "[1:a]adelay=5000:all=1,volume=1.0[a0]" in _fc(argv)
    assert "[2:a]adelay=7500:all=1,volume=0.8[a1]" in _fc(argv)
    assert "[a0][a1]amix=inputs=2:normalize=0:dropout_transition=0[a]" in _fc(argv)
    assert ("-map", "[a]") in _pairs(argv)


def test_encode_tail():
    op = ComposeVideo(
        asset=_base(),
        layers=[_layer()],
        audio_layers=[
            ComposeAudioLayer(
                asset=MediaAsset(mime_type="audio/wav", provider="test", uri="n.wav")
            )
        ],
        encode=EncodeSpec(codec="hevc_nvenc", bitrate="10M", resolution="1080x1920", fps=30),
    )
    argv = build_compose_argv(
        op, input_paths=["base.mp4", "layer.mov", "n.wav"], output_path="out.mp4"
    )
    assert argv[argv.index("-map") :] == [
        "-map",
        "[v0]",
        "-map",
        "[a]",
        "-c:v",
        "hevc_nvenc",
        "-b:v",
        "10M",
        "-s",
        "1080x1920",
        "-r",
        "30",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "out.mp4",
    ]


def test_empty_compose_is_copy_fast_path():
    op = ComposeVideo(asset=_base())
    argv = build_compose_argv(op, input_paths=["base.mp4"], output_path="out.mp4")
    assert argv == ["ffmpeg", "-y", "-i", "base.mp4", "-c", "copy", "out.mp4"]
