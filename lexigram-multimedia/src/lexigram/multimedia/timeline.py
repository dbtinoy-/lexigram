"""Timeline: a mutable builder for composing clips + narration + music + captions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.multimedia.protocols import VideoProcessor
from lexigram.contracts.multimedia.types import (
    BurnSubtitles,
    Concat,
    MediaAsset,
    MuxAudio,
    SubtitleCue,
    TransitionSpec,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.result import Result
    from lexigram.contracts.multimedia.exceptions import VideoGenerationError


class Timeline:
    """Builds up a video composition spec; render() executes it via a VideoProcessor."""

    def __init__(self) -> None:
        self._clips: list[MediaAsset] = []
        # One entry per adjacent clip pair (len == len(clips) - 1), describing
        # the transition joining clip[i] to clip[i+1]. A clip's transition_in
        # only makes sense once a previous clip exists, so the very first
        # add_clip()'s transition_in is intentionally discarded.
        self._transitions: list[TransitionSpec] = []
        self._narration: MediaAsset | None = None
        self._music: MediaAsset | None = None
        self._duck_under_narration: bool = False
        self._captions: list[SubtitleCue] = []

    def add_clip(
        self, asset: MediaAsset, *, transition_in: TransitionSpec | None = None
    ) -> Timeline:
        if self._clips:
            self._transitions.append(transition_in or TransitionSpec(kind="cut"))
        self._clips.append(asset)
        return self

    def set_narration(self, asset: MediaAsset) -> Timeline:
        self._narration = asset
        return self

    def set_music(
        self, asset: MediaAsset, *, duck_under_narration: bool = False
    ) -> Timeline:
        self._music = asset
        self._duck_under_narration = duck_under_narration
        return self

    def add_captions(self, cues: list[SubtitleCue]) -> Timeline:
        self._captions.extend(cues)
        return self

    async def render(
        self, processor: VideoProcessor
    ) -> Result[MediaAsset, VideoGenerationError]:
        from lexigram.contracts.core.result import Ok

        result = await processor.process(
            Concat(assets=self._clips, transitions=self._transitions or None)
        )
        if result.is_err():
            return result
        current = result.unwrap()

        if self._narration is not None:
            result = await processor.process(
                MuxAudio(asset=current, audio_asset=self._narration, mode="replace")
            )
            if result.is_err():
                return result
            current = result.unwrap()

        if self._music is not None:
            result = await processor.process(
                MuxAudio(
                    asset=current,
                    audio_asset=self._music,
                    mode="mix",
                    duck_under_existing=self._duck_under_narration,
                )
            )
            if result.is_err():
                return result
            current = result.unwrap()

        if self._captions:
            result = await processor.process(
                BurnSubtitles(asset=current, cues=self._captions)
            )
            if result.is_err():
                return result
            current = result.unwrap()

        return Ok(current)

    @property
    def clips(self) -> list[MediaAsset]:
        return list(self._clips)

    @property
    def transitions(self) -> list[TransitionSpec]:
        return list(self._transitions)

    @property
    def narration(self) -> MediaAsset | None:
        return self._narration

    @property
    def music(self) -> MediaAsset | None:
        return self._music

    @property
    def duck_under_narration(self) -> bool:
        return self._duck_under_narration

    @property
    def captions(self) -> list[SubtitleCue]:
        return list(self._captions)

    def to_params(self) -> dict[str, Any]:
        return {
            "clips": [_asset_to_dict(c) for c in self._clips],
            "transitions": [
                {"kind": t.kind, "duration": t.duration} for t in self._transitions
            ],
            "narration": _asset_to_dict(self._narration) if self._narration else None,
            "music": _asset_to_dict(self._music) if self._music else None,
            "duck_under_narration": self._duck_under_narration,
            "captions": [
                {"start": c.start, "end": c.end, "text": c.text} for c in self._captions
            ],
        }

    @classmethod
    def from_params(cls, params: dict[str, Any]) -> Timeline:
        timeline = cls()
        transitions = params.get("transitions", [])
        for i, clip_data in enumerate(params["clips"]):
            transition_in = (
                TransitionSpec(**transitions[i - 1])
                if i > 0 and i - 1 < len(transitions)
                else None
            )
            timeline.add_clip(_asset_from_dict(clip_data), transition_in=transition_in)
        if params.get("narration"):
            timeline.set_narration(_asset_from_dict(params["narration"]))
        if params.get("music"):
            timeline.set_music(
                _asset_from_dict(params["music"]),
                duck_under_narration=params.get("duck_under_narration", False),
            )
        if params.get("captions"):
            timeline.add_captions([SubtitleCue(**c) for c in params["captions"]])
        return timeline


def _asset_to_dict(asset: MediaAsset) -> dict[str, Any]:
    return {
        "mime_type": asset.mime_type,
        "provider": asset.provider,
        "bytes_data": asset.bytes_data,
        "uri": asset.uri,
        "metadata": asset.metadata,
    }


def _asset_from_dict(data: dict[str, Any]) -> MediaAsset:
    return MediaAsset(
        mime_type=data["mime_type"],
        provider=data["provider"],
        bytes_data=data.get("bytes_data"),
        uri=data.get("uri"),
        metadata=data.get("metadata", {}),
    )


__all__ = ["Timeline"]
