from lexigram.contracts.multimedia.types import (
    BurnSubtitles,
    ChangeSpeed,
    ColorFilter,
    Concat,
    Crop,
    ExtractThumbnail,
    MediaAsset,
    MuxAudio,
    OverlayImage,
    OverlayText,
    RawFilter,
    SubtitleCue,
    ToGif,
    Transcode,
    TransitionSpec,
    Trim,
    VideoOperation,
)


def test_trim_is_frozen_dataclass():
    asset = MediaAsset(mime_type="video/mp4", provider="local-http", uri="a.mp4")
    op = Trim(asset=asset, start=1.0, end=2.0)
    assert op.start == 1.0
    assert op.end == 2.0


def test_concat_accepts_optional_transitions():
    asset = MediaAsset(mime_type="video/mp4", provider="local-http", uri="a.mp4")
    op = Concat(
        assets=[asset, asset],
        transitions=[TransitionSpec(kind="crossfade", duration=0.5)],
    )
    assert len(op.transitions) == 1
    assert op.transitions[0].kind == "crossfade"


def test_overlay_text_position_and_defaults():
    asset = MediaAsset(mime_type="video/mp4", provider="local-http", uri="a.mp4")
    op = OverlayText(asset=asset, text="hi", position="bottom")
    assert op.font_size == 32
    assert op.color == "white"


def test_burn_subtitles_cues():
    asset = MediaAsset(mime_type="video/mp4", provider="local-http", uri="a.mp4")
    op = BurnSubtitles(asset=asset, cues=[SubtitleCue(start=0.0, end=1.0, text="hi")])
    assert op.cues[0].text == "hi"


def test_video_operation_union_matches_all_variants():
    asset = MediaAsset(mime_type="video/mp4", provider="local-http", uri="a.mp4")
    ops: list[VideoOperation] = [
        Trim(asset=asset, start=0.0, end=1.0),
        Concat(assets=[asset]),
        OverlayText(asset=asset, text="hi", position="top"),
        OverlayImage(asset=asset, image_asset=asset, position="top"),
        BurnSubtitles(asset=asset, cues=[]),
        MuxAudio(asset=asset, audio_asset=asset, mode="replace"),
        ExtractThumbnail(asset=asset, timestamp=0.0),
        ToGif(asset=asset),
        Transcode(asset=asset, format="webm"),
        ChangeSpeed(asset=asset, factor=2.0),
        Crop(asset=asset, x=0, y=0, width=10, height=10),
        ColorFilter(asset=asset, preset="grayscale"),
        RawFilter(assets=[asset], filter_complex="null", maps=["0:v"]),
    ]
    for op in ops:
        match op:
            case (
                Trim()
                | Concat()
                | OverlayText()
                | OverlayImage()
                | BurnSubtitles()
                | MuxAudio()
                | ExtractThumbnail()
                | ToGif()
                | Transcode()
                | ChangeSpeed()
                | Crop()
                | ColorFilter()
                | RawFilter()
            ):
                pass
            case _:
                raise AssertionError(f"unmatched: {op}")
