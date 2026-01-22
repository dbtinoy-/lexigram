from lexigram.contracts.multimedia.types import (
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
