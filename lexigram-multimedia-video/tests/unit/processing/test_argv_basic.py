import pytest

from lexigram.contracts.multimedia.types import (
    ChangeSpeed,
    ColorFilter,
    Crop,
    MediaAsset,
    Transcode,
    Trim,
)
from lexigram.multimedia.video.processing.argv import build_argv

ASSET = MediaAsset(mime_type="video/mp4", provider="local-http", uri="a.mp4")


def test_trim_argv():
    op = Trim(asset=ASSET, start=1.5, end=4.0)
    argv = build_argv(op, input_paths=["in.mp4"], output_path="out.mp4", ffmpeg_binary="ffmpeg")
    assert argv == [
        "ffmpeg",
        "-y",
        "-ss",
        "1.5",
        "-to",
        "4.0",
        "-i",
        "in.mp4",
        "-c",
        "copy",
        "out.mp4",
    ]


def test_crop_argv():
    op = Crop(asset=ASSET, x=10, y=20, width=100, height=200)
    argv = build_argv(op, input_paths=["in.mp4"], output_path="out.mp4", ffmpeg_binary="ffmpeg")
    assert argv == [
        "ffmpeg",
        "-y",
        "-i",
        "in.mp4",
        "-vf",
        "crop=100:200:10:20",
        "out.mp4",
    ]


def test_change_speed_argv():
    op = ChangeSpeed(asset=ASSET, factor=2.0)
    argv = build_argv(op, input_paths=["in.mp4"], output_path="out.mp4", ffmpeg_binary="ffmpeg")
    assert argv == [
        "ffmpeg",
        "-y",
        "-i",
        "in.mp4",
        "-filter_complex",
        "[0:v]setpts=0.5*PTS[v];[0:a]atempo=2.0[a]",
        "-map",
        "[v]",
        "-map",
        "[a]",
        "out.mp4",
    ]


def test_color_filter_argv_with_preset():
    op = ColorFilter(asset=ASSET, preset="grayscale")
    argv = build_argv(op, input_paths=["in.mp4"], output_path="out.mp4", ffmpeg_binary="ffmpeg")
    assert argv == [
        "ffmpeg",
        "-y",
        "-i",
        "in.mp4",
        "-vf",
        "hue=s=0",
        "out.mp4",
    ]


def test_color_filter_argv_with_manual_eq():
    op = ColorFilter(asset=ASSET, brightness=0.1, contrast=1.2, saturation=0.8)
    argv = build_argv(op, input_paths=["in.mp4"], output_path="out.mp4", ffmpeg_binary="ffmpeg")
    assert argv == [
        "ffmpeg",
        "-y",
        "-i",
        "in.mp4",
        "-vf",
        "eq=brightness=0.1:contrast=1.2:saturation=0.8",
        "out.mp4",
    ]


def test_transcode_argv_full():
    op = Transcode(
        asset=ASSET, format="webm", codec="libvpx-vp9", resolution="1280x720", bitrate="1M"
    )
    argv = build_argv(op, input_paths=["in.mp4"], output_path="out.webm", ffmpeg_binary="ffmpeg")
    assert argv == [
        "ffmpeg",
        "-y",
        "-i",
        "in.mp4",
        "-c:v",
        "libvpx-vp9",
        "-s",
        "1280x720",
        "-b:v",
        "1M",
        "out.webm",
    ]


@pytest.mark.parametrize("good", ["1920x1080", "1280x720"])
def test_valid_resolutions_accepted(good: str) -> None:
    from lexigram.multimedia.video.processing.argv import build_argv

    argv = build_argv(
        Transcode(asset=ASSET, format="mp4", resolution=good),
        input_paths=["in.mp4"],
        output_path="out.mp4",
    )
    assert ("-s", good) in list(zip(argv, argv[1:]))


@pytest.mark.parametrize("bad", ["720x1280;rm", "1920x1080:extra"])
def test_hostile_resolution_rejected(bad: str) -> None:
    from lexigram.multimedia.video.processing.argv import build_argv

    with pytest.raises(ValueError):
        build_argv(
            Transcode(asset=ASSET, format="mp4", resolution=bad),
            input_paths=["in.mp4"],
            output_path="out.mp4",
        )


def test_valid_bitrate_accepted() -> None:
    from lexigram.multimedia.video.processing.argv import build_argv

    argv = build_argv(
        Transcode(asset=ASSET, format="mp4", bitrate="2M"),
        input_paths=["in.mp4"],
        output_path="out.mp4",
    )
    assert ("-b:v", "2M") in list(zip(argv, argv[1:]))


@pytest.mark.parametrize("bad", ["2M:y=0", "2M;x", "-2M"])
def test_hostile_bitrate_rejected(bad: str) -> None:
    from lexigram.multimedia.video.processing.argv import build_argv

    with pytest.raises(ValueError):
        build_argv(
            Transcode(asset=ASSET, format="mp4", bitrate=bad),
            input_paths=["in.mp4"],
            output_path="out.mp4",
        )


@pytest.mark.parametrize("codec", ["libx264", "h264", "libvpx-vp9", "copy", "aac"])
def test_allowlisted_codecs_accepted(codec: str) -> None:
    from lexigram.multimedia.video.processing.argv import build_argv

    argv = build_argv(
        Transcode(asset=ASSET, format="mp4", codec=codec),
        input_paths=["in.mp4"],
        output_path="out.mp4",
    )
    assert ("-c:v", codec) in list(zip(argv, argv[1:]))


@pytest.mark.parametrize("bad", ["x;movie=/etc/passwd", "libx264:extra", "../evil"])
def test_hostile_codec_rejected(bad: str) -> None:
    from lexigram.multimedia.video.processing.argv import build_argv

    with pytest.raises(ValueError):
        build_argv(
            Transcode(asset=ASSET, format="mp4", codec=bad),
            input_paths=["in.mp4"],
            output_path="out.mp4",
        )
