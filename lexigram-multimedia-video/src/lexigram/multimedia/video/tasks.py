"""Task handler registered with lexigram-tasks for the submit() job path."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.multimedia.protocols import VideoProcessor, VideoProvider
    from lexigram.contracts.multimedia.types import VideoOperation


class VideoGenerationTask:
    """Callable task handler — wraps a VideoProvider backend for lexigram-tasks.

    Returns a plain dict (never raw MediaAsset bytes) because lexigram-tasks'
    result store JSON-serializes JobResult. The umbrella wraps this handler
    during MultimediaProvider.register() to persist any bytes to
    lexigram-storage BEFORE this dict is constructed — see the "Async job
    model" section of the design spec.
    """

    def __init__(self, backend: VideoProvider) -> None:
        self._backend = backend

    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        from lexigram.contracts.multimedia.types import VideoRequest

        raw_duration = params.get("duration_seconds")
        request = VideoRequest(
            prompt=params["prompt"],
            duration_seconds=(float(raw_duration) if raw_duration is not None else 4.0),
            resolution=params.get("resolution", "1280x720"),
            image_uri=params.get("image_uri"),
            format=params.get("format", "mp4"),
        )
        result = await self._backend.generate(request)
        if result.is_err():
            raise result.unwrap_err()

        asset = result.unwrap()
        return {
            "provider": asset.provider,
            "mime_type": asset.mime_type,
            "bytes_data": asset.bytes_data,
            "uri": asset.uri,
            "metadata": asset.metadata,
        }


__all__ = ["VideoGenerationTask", "VideoProcessingTask"]


class VideoProcessingTask:
    """Task handler for the async video processing job path.

    Reconstructs a VideoOperation variant from a flat params dict using the
    ``operation_type`` discriminator (the dataclass's class name), matching
    the pattern ``Timeline.from_params()`` uses for timeline renders.
    """

    def __init__(self, backend: VideoProcessor) -> None:
        self._backend = backend

    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        operation = _operation_from_params(params)
        result = await self._backend.process(operation)
        if result.is_err():
            raise result.unwrap_err()
        asset = result.unwrap()
        return {
            "provider": asset.provider,
            "mime_type": asset.mime_type,
            "bytes_data": asset.bytes_data,
            "uri": asset.uri,
            "metadata": asset.metadata,
        }


def _asset_from_params(data: dict[str, Any]) -> MediaAsset:
    from lexigram.contracts.multimedia.types import MediaAsset

    return MediaAsset(
        mime_type=data["mime_type"],
        provider=data["provider"],
        bytes_data=data.get("bytes_data"),
        uri=data.get("uri"),
        metadata=data.get("metadata", {}),
    )


def _operation_from_params(params: dict[str, Any]) -> VideoOperation:
    from lexigram.contracts.multimedia.types import (
        BurnSubtitles,
        ChangeSpeed,
        ColorFilter,
        Concat,
        Crop,
        ExtractThumbnail,
        MuxAudio,
        OverlayImage,
        OverlayText,
        RawFilter,
        SubtitleCue,
        ToGif,
        Transcode,
        TransitionSpec,
        Trim,
    )

    kind = params["operation_type"]
    if kind == "Trim":
        return Trim(
            asset=_asset_from_params(params["asset"]),
            start=params["start"],
            end=params["end"],
        )
    if kind == "Concat":
        transitions = params.get("transitions")
        return Concat(
            assets=[_asset_from_params(a) for a in params["assets"]],
            transitions=[TransitionSpec(**t) for t in transitions]
            if transitions
            else None,
        )
    if kind == "OverlayText":
        return OverlayText(
            asset=_asset_from_params(params["asset"]),
            text=params["text"],
            position=params["position"],
            start=params.get("start"),
            end=params.get("end"),
            font_size=params.get("font_size", 32),
            color=params.get("color", "white"),
        )
    if kind == "OverlayImage":
        return OverlayImage(
            asset=_asset_from_params(params["asset"]),
            image_asset=_asset_from_params(params["image_asset"]),
            position=params["position"],
            opacity=params.get("opacity", 1.0),
            start=params.get("start"),
            end=params.get("end"),
        )
    if kind == "BurnSubtitles":
        return BurnSubtitles(
            asset=_asset_from_params(params["asset"]),
            cues=[SubtitleCue(**c) for c in params["cues"]],
        )
    if kind == "MuxAudio":
        return MuxAudio(
            asset=_asset_from_params(params["asset"]),
            audio_asset=_asset_from_params(params["audio_asset"]),
            mode=params["mode"],
            music_volume=params.get("music_volume", 1.0),
            duck_under_existing=params.get("duck_under_existing", False),
        )
    if kind == "ExtractThumbnail":
        return ExtractThumbnail(
            asset=_asset_from_params(params["asset"]), timestamp=params["timestamp"]
        )
    if kind == "ToGif":
        return ToGif(
            asset=_asset_from_params(params["asset"]),
            start=params.get("start"),
            end=params.get("end"),
            fps=params.get("fps", 10),
            width=params.get("width", 480),
        )
    if kind == "Transcode":
        return Transcode(
            asset=_asset_from_params(params["asset"]),
            format=params["format"],
            codec=params.get("codec"),
            resolution=params.get("resolution"),
            bitrate=params.get("bitrate"),
        )
    if kind == "ChangeSpeed":
        return ChangeSpeed(
            asset=_asset_from_params(params["asset"]), factor=params["factor"]
        )
    if kind == "Crop":
        return Crop(
            asset=_asset_from_params(params["asset"]),
            x=params["x"],
            y=params["y"],
            width=params["width"],
            height=params["height"],
        )
    if kind == "ColorFilter":
        return ColorFilter(
            asset=_asset_from_params(params["asset"]),
            preset=params.get("preset"),
            brightness=params.get("brightness", 0.0),
            contrast=params.get("contrast", 1.0),
            saturation=params.get("saturation", 1.0),
        )
    if kind == "RawFilter":
        return RawFilter(
            assets=[_asset_from_params(a) for a in params["assets"]],
            filter_complex=params["filter_complex"],
            maps=params["maps"],
            extra_args=params.get("extra_args", []),
        )
    raise ValueError(f"unknown operation_type: {kind!r}")
