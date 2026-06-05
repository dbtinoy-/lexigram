import pytest

from lexigram.contracts.multimedia.types import (
    BurnSubtitles,
    Concat,
    ExtractThumbnail,
    MediaAsset,
    MuxAudio,
    OverlayImage,
    OverlayText,
    RawFilter,
    SubtitleCue,
    ToGif,
    TransitionSpec,
)
from lexigram.multimedia.video.processing.argv import build_argv, cues_to_srt

ASSET = MediaAsset(mime_type="video/mp4", provider="local-http", uri="a.mp4")


def test_concat_without_transitions_uses_plain_concat_filter():
    op = Concat(assets=[ASSET, ASSET])
    argv = build_argv(op, input_paths=["a.mp4", "b.mp4"], output_path="out.mp4")
    assert "-filter_complex" in argv
    fc = argv[argv.index("-filter_complex") + 1]
    assert fc == "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]"


def test_concat_with_single_crossfade_uses_xfade():
    op = Concat(
        assets=[ASSET, ASSET],
        transitions=[TransitionSpec(kind="crossfade", duration=0.5)],
    )
    argv = build_argv(
        op,
        input_paths=["a.mp4", "b.mp4"],
        output_path="out.mp4",
        clip_durations=[3.0, 3.0],
    )
    fc = argv[argv.index("-filter_complex") + 1]
    assert "xfade=transition=fade:duration=0.5:offset=2.5" in fc
    assert "acrossfade=d=0.5" in fc


def test_concat_with_mixed_cut_and_crossfade_only_blends_the_crossfade_pair():
    # Three clips, two gaps: a hard cut into clip 1, then a crossfade into clip 2.
    # Only the second gap should carry a real crossfade duration — a "cut" gap
    # must NOT inherit the 0.5s default just because some other gap in the same
    # Concat is a crossfade. A cut is expressed as the 1/30s epsilon xfade (not
    # exactly 0.0 — verified against real ffmpeg 6.1.1, where a 0.0 offset at
    # the exact segment end silently truncates the rest of the chain).
    op = Concat(
        assets=[ASSET, ASSET, ASSET],
        transitions=[
            TransitionSpec(kind="cut"),
            TransitionSpec(kind="crossfade", duration=0.5),
        ],
    )
    argv = build_argv(
        op,
        input_paths=["a.mp4", "b.mp4", "c.mp4"],
        output_path="out.mp4",
        clip_durations=[3.0, 3.0, 3.0],
    )
    fc = argv[argv.index("-filter_complex") + 1]
    assert "xfade=transition=fade:duration=0.03333333333333333:offset=2.966666666666667[v1]" in fc
    assert "acrossfade=d=0.03333333333333333[a1]" in fc
    assert "xfade=transition=fade:duration=0.5:offset=5.466666666666667[v2]" in fc
    assert "acrossfade=d=0.5[a2]" in fc


def test_overlay_text_argv_basic():
    op = OverlayText(asset=ASSET, text="hello", position="top")
    argv = build_argv(op, input_paths=["in.mp4"], output_path="out.mp4")
    assert argv[0] == "ffmpeg"
    assert "-vf" in argv
    vf = argv[argv.index("-vf") + 1]
    assert "drawtext=text='hello'" in vf
    assert "fontsize=32" in vf


def test_overlay_text_argv_with_timing():
    op = OverlayText(asset=ASSET, text="hi", position="bottom", start=1.0, end=2.0)
    argv = build_argv(op, input_paths=["in.mp4"], output_path="out.mp4")
    vf = argv[argv.index("-vf") + 1]
    assert "enable='between(t,1.0,2.0)'" in vf


def test_overlay_image_argv():
    op = OverlayImage(asset=ASSET, image_asset=ASSET, position="top-left")
    argv = build_argv(op, input_paths=["in.mp4", "logo.png"], output_path="out.mp4")
    assert argv[:5] == ["ffmpeg", "-y", "-i", "in.mp4", "-i"]
    assert "logo.png" in argv


def test_burn_subtitles_argv():
    op = BurnSubtitles(
        asset=ASSET, cues=[SubtitleCue(start=0.0, end=1.0, text="hi")]
    )
    argv = build_argv(
        op, input_paths=["in.mp4"], output_path="out.mp4", subtitle_path="subs.srt"
    )
    assert argv == [
        "ffmpeg",
        "-y",
        "-i",
        "in.mp4",
        "-vf",
        "subtitles=subs.srt",
        "out.mp4",
    ]


def test_cues_to_srt_format():
    cues = [SubtitleCue(start=0.0, end=1.5, text="hello")]
    srt = cues_to_srt(cues)
    assert "1\n00:00:00,000 --> 00:00:01,500\nhello" in srt


def test_mux_audio_replace_argv():
    op = MuxAudio(asset=ASSET, audio_asset=ASSET, mode="replace")
    argv = build_argv(
        op, input_paths=["video.mp4", "narration.mp3"], output_path="out.mp4"
    )
    assert argv == [
        "ffmpeg",
        "-y",
        "-i",
        "video.mp4",
        "-i",
        "narration.mp3",
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-c:v",
        "copy",
        "-shortest",
        "out.mp4",
    ]


def test_mux_audio_mix_with_ducking_argv():
    op = MuxAudio(
        asset=ASSET,
        audio_asset=ASSET,
        mode="mix",
        music_volume=0.3,
        duck_under_existing=True,
    )
    argv = build_argv(
        op, input_paths=["video.mp4", "music.mp3"], output_path="out.mp4"
    )
    assert "-filter_complex" in argv
    fc = argv[argv.index("-filter_complex") + 1]
    # music (index 1) must be the signal being compressed, controlled by the
    # existing/narration track (index 0) — not the other way around.
    assert "[music][0:a]sidechaincompress" in fc
    assert "volume=0.3" in fc


def test_extract_thumbnail_argv():
    op = ExtractThumbnail(asset=ASSET, timestamp=3.0)
    argv = build_argv(op, input_paths=["in.mp4"], output_path="thumb.png")
    assert argv == [
        "ffmpeg",
        "-y",
        "-ss",
        "3.0",
        "-i",
        "in.mp4",
        "-frames:v",
        "1",
        "thumb.png",
    ]


def test_to_gif_argv():
    op = ToGif(asset=ASSET, start=1.0, end=3.0, fps=15, width=320)
    argv = build_argv(op, input_paths=["in.mp4"], output_path="out.gif")
    assert argv == [
        "ffmpeg",
        "-y",
        "-ss",
        "1.0",
        "-to",
        "3.0",
        "-i",
        "in.mp4",
        "-vf",
        "fps=15,scale=320:-1:flags=lanczos",
        "out.gif",
    ]


def test_raw_filter_argv_escape_hatch():
    op = RawFilter(
        assets=[ASSET],
        filter_complex="[0:v]null[v]",
        maps=["[v]"],
        extra_args=["-preset", "fast"],
    )
    argv = build_argv(op, input_paths=["in.mp4"], output_path="out.mp4")
    assert argv == [
        "ffmpeg",
        "-y",
        "-i",
        "in.mp4",
        "-filter_complex",
        "[0:v]null[v]",
        "-map",
        "[v]",
        "-preset",
        "fast",
        "out.mp4",
    ]


def _op(**kw) -> OverlayText:
    base = dict(
        asset=MediaAsset(mime_type="video/mp4", provider="t"),
        text="hi",
        position="center",
    )
    base.update(kw)
    return OverlayText(**base)


@pytest.mark.parametrize("color", ["white':x=0:y=0,drawtext=", "red:alpha=0.5"])
def test_overlay_color_injection_rejected(color: str) -> None:
    from lexigram.multimedia.video.processing.argv import build_argv

    with pytest.raises(ValueError):
        build_argv(_op(color=color), input_paths=["a.mp4"], output_path="o.mp4")


def test_overlay_font_size_out_of_range_rejected() -> None:
    from lexigram.multimedia.video.processing.argv import build_argv

    with pytest.raises(ValueError):
        build_argv(_op(font_size=10_000), input_paths=["a.mp4"], output_path="o.mp4")


@pytest.mark.parametrize("good", ["white", "red", "0x00FF00", "black"])
def test_valid_colors_still_accepted(good: str) -> None:
    from lexigram.multimedia.video.processing.argv import build_argv

    assert "fontcolor=" in " ".join(
        build_argv(_op(color=good), input_paths=["a.mp4"], output_path="o.mp4")
    )
