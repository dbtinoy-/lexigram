from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Err, Ok
from lexigram.contracts.multimedia.types import (
    BurnSubtitles,
    Concat,
    MediaAsset,
    MuxAudio,
    SubtitleCue,
    TransitionSpec,
)
from lexigram.multimedia.timeline import Timeline

CLIP = MediaAsset(mime_type="video/mp4", provider="local-http", uri="clip1.mp4")
NARRATION = MediaAsset(mime_type="audio/mpeg", provider="elevenlabs", uri="narr.mp3")
MUSIC = MediaAsset(mime_type="audio/mpeg", provider="local-http", uri="music.mp3")


def _out(tag: str) -> MediaAsset:
    return MediaAsset(mime_type="video/mp4", provider="ffmpeg", uri=f"{tag}.mp4")


@pytest.mark.asyncio
async def test_render_clips_only_calls_concat_alone() -> None:
    processor = AsyncMock()
    processor.process.return_value = Ok(_out("concat"))

    timeline = Timeline().add_clip(CLIP).add_clip(CLIP)
    result = await timeline.render(processor)

    assert result.is_ok()
    assert result.unwrap() == _out("concat")
    processor.process.assert_awaited_once()
    op = processor.process.call_args[0][0]
    assert isinstance(op, Concat)


@pytest.mark.asyncio
async def test_render_passes_clip_transitions_into_concat() -> None:
    processor = AsyncMock()
    processor.process.return_value = Ok(_out("concat"))

    timeline = (
        Timeline()
        .add_clip(CLIP)
        .add_clip(CLIP, transition_in=TransitionSpec(kind="crossfade", duration=0.5))
    )
    await timeline.render(processor)

    op = processor.process.call_args[0][0]
    assert isinstance(op, Concat)
    assert op.transitions == [TransitionSpec(kind="crossfade", duration=0.5)]


@pytest.mark.asyncio
async def test_render_full_pipeline_sequences_all_stages() -> None:
    processor = AsyncMock()
    processor.process.side_effect = [
        Ok(_out("concat")),
        Ok(_out("narrated")),
        Ok(_out("mixed")),
        Ok(_out("captioned")),
    ]

    timeline = (
        Timeline()
        .add_clip(CLIP)
        .set_narration(NARRATION)
        .set_music(MUSIC, duck_under_narration=True)
        .add_captions([SubtitleCue(start=0.0, end=1.0, text="hi")])
    )
    result = await timeline.render(processor)

    assert result.is_ok()
    assert result.unwrap() == _out("captioned")
    assert processor.process.await_count == 4

    calls = [c[0][0] for c in processor.process.call_args_list]
    assert isinstance(calls[0], Concat)
    assert isinstance(calls[1], MuxAudio)
    assert calls[1].mode == "replace"
    assert calls[1].asset == _out("concat")
    assert isinstance(calls[2], MuxAudio)
    assert calls[2].mode == "mix"
    assert calls[2].duck_under_existing is True
    assert isinstance(calls[3], BurnSubtitles)
    assert calls[3].asset == _out("mixed")


@pytest.mark.asyncio
async def test_render_music_without_narration_still_mixes() -> None:
    processor = AsyncMock()
    processor.process.side_effect = [Ok(_out("concat")), Ok(_out("mixed"))]

    timeline = Timeline().add_clip(CLIP).set_music(MUSIC)
    result = await timeline.render(processor)

    assert result.is_ok()
    assert processor.process.await_count == 2
    mux_op = processor.process.call_args_list[1][0][0]
    assert mux_op.asset == _out("concat")
    assert mux_op.duck_under_existing is False


@pytest.mark.asyncio
async def test_render_short_circuits_on_error() -> None:
    processor = AsyncMock()
    err = Err(ValueError("concat failed"))
    processor.process.return_value = err

    timeline = Timeline().add_clip(CLIP).set_narration(NARRATION)
    result = await timeline.render(processor)

    assert result.is_err()
    processor.process.assert_awaited_once()
