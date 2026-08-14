from lexigram.contracts.multimedia.types import (
    EncodeSpec,
    MediaAsset,
    SubtitleCue,
    TransitionSpec,
)
from lexigram.multimedia.timeline import Timeline

CLIP = MediaAsset(mime_type="video/mp4", provider="local-http", uri="clip1.mp4")
NARRATION = MediaAsset(mime_type="audio/mpeg", provider="elevenlabs", uri="narr.mp3")
MUSIC = MediaAsset(mime_type="audio/mpeg", provider="local-http", uri="music.mp3")


def test_builder_fluent_api() -> None:
    timeline = Timeline()
    timeline.add_clip(CLIP)
    timeline.set_narration(NARRATION)
    timeline.set_music(MUSIC, duck_under_narration=True)
    timeline.add_captions([SubtitleCue(start=0.0, end=1.0, text="hi")])

    assert timeline.clips == [CLIP]
    assert timeline.narration == NARRATION
    assert timeline.music == MUSIC
    assert timeline.duck_under_narration is True
    assert timeline.captions == [SubtitleCue(start=0.0, end=1.0, text="hi")]


def test_add_clip_appends_multiple() -> None:
    timeline = Timeline()
    timeline.add_clip(CLIP)
    timeline.add_clip(CLIP)
    assert len(timeline.clips) == 2


def test_add_clip_with_transition_in_tracks_transitions_between_clips() -> None:
    timeline = Timeline()
    timeline.add_clip(CLIP)
    timeline.add_clip(
        CLIP, transition_in=TransitionSpec(kind="crossfade", duration=0.5)
    )
    timeline.add_clip(CLIP)  # no transition_in -> defaults to a hard cut

    # transitions has one entry per adjacent clip pair (len(clips) - 1),
    # aligned with what Concat(assets, transitions) expects in Task 13.
    assert timeline.transitions == [
        TransitionSpec(kind="crossfade", duration=0.5),
        TransitionSpec(kind="cut"),
    ]


def test_first_clips_transition_in_is_ignored() -> None:
    timeline = Timeline()
    # A transition_in on the very first clip has nothing to transition
    # from, so it must not appear in `transitions` at all.
    timeline.add_clip(
        CLIP, transition_in=TransitionSpec(kind="crossfade", duration=0.5)
    )
    assert timeline.transitions == []


def test_to_params_and_from_params_roundtrip() -> None:
    timeline = Timeline()
    timeline.add_clip(CLIP)
    timeline.add_clip(
        CLIP, transition_in=TransitionSpec(kind="crossfade", duration=0.5)
    )
    timeline.set_narration(NARRATION)
    timeline.set_music(MUSIC, duck_under_narration=True)
    timeline.add_captions([SubtitleCue(start=0.0, end=1.0, text="hi")])

    params = timeline.to_params()
    restored = Timeline.from_params(params)

    assert restored.clips == timeline.clips
    assert restored.transitions == timeline.transitions
    assert restored.narration == timeline.narration
    assert restored.music == timeline.music
    assert restored.duck_under_narration == timeline.duck_under_narration
    assert restored.captions == timeline.captions


def test_to_params_with_no_optional_fields() -> None:
    timeline = Timeline()
    timeline.add_clip(CLIP)
    params = timeline.to_params()
    restored = Timeline.from_params(params)
    assert restored.narration is None
    assert restored.music is None
    assert restored.captions == []
    assert restored.transitions == []


def test_timeline_compose_fields_fluent_api() -> None:
    base = MediaAsset(mime_type="video/mp4", provider="test", uri="b.mp4")
    layer = MediaAsset(mime_type="video/quicktime", provider="test", uri="l.mov")
    audio = MediaAsset(mime_type="audio/wav", provider="test", uri="n.wav")
    timeline = Timeline()
    timeline.add_clip(base)
    timeline.add_overlay(layer, start=1.0, end=3.0, fade_in=0.2, fade_out=0.3)
    timeline.add_audio(audio, start=2.0, volume=0.8)
    timeline.set_fade_in(0.5)
    timeline.set_fade_out(0.5)
    timeline.set_base_fade_out(0.75)
    timeline.set_encode(EncodeSpec(codec="hevc_nvenc", fps=30))

    assert len(timeline.overlays) == 1
    assert timeline.overlays[0].fade_in == 0.2
    assert timeline.audio_layers[0].volume == 0.8
    assert timeline.fade_in == 0.5
    assert timeline.base_fade_out == 0.75
    assert timeline.encode is not None
    assert timeline.encode.codec == "hevc_nvenc"


def test_timeline_params_roundtrip_with_compose_fields() -> None:
    timeline = Timeline()
    timeline.add_clip(MediaAsset(mime_type="video/mp4", provider="test", uri="b.mp4"))
    timeline.add_overlay(
        MediaAsset(mime_type="video/quicktime", provider="test", uri="l.mov"),
        start=1.0,
    )
    timeline.add_audio(
        MediaAsset(mime_type="audio/wav", provider="test", uri="n.wav"),
        start=2.0,
        volume=0.5,
    )
    timeline.set_fade_out(0.5)
    timeline.set_encode(
        EncodeSpec(codec="hevc_nvenc", resolution="1080x1920", fps=30)
    )
    restored = Timeline.from_params(timeline.to_params())
    assert restored.to_params() == timeline.to_params()


def test_defaults_unchanged() -> None:
    timeline = Timeline()
    timeline.add_clip(MediaAsset(mime_type="video/mp4", provider="test", uri="b.mp4"))
    assert timeline.overlays == []
    assert timeline.audio_layers == []
    assert timeline.fade_in == 0.0
    assert timeline.encode is None
    assert "overlays" in timeline.to_params()
