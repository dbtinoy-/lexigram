"""Task handler registered with lexigram-tasks for the submit() job path."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.multimedia.protocols import InterpolationProvider
    from lexigram.contracts.multimedia.types import MediaAsset


def _asset_from_params(data: dict[str, Any]) -> MediaAsset:
    from lexigram.contracts.multimedia.types import MediaAsset

    return MediaAsset(
        mime_type=data["mime_type"],
        provider=data["provider"],
        bytes_data=data.get("bytes_data"),
        uri=data.get("uri"),
        metadata=data.get("metadata", {}),
    )


class InterpolationTask:
    """Callable task handler — wraps an InterpolationProvider backend for lexigram-tasks.

    Returns a plain dict (never raw MediaAsset bytes) because lexigram-tasks'
    result store JSON-serializes JobResult. The umbrella wraps this handler
    during MultimediaProvider.register() to persist any bytes to
    lexigram-storage BEFORE this dict is constructed.
    """

    def __init__(self, backend: InterpolationProvider) -> None:
        self._backend = backend

    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        from lexigram.contracts.multimedia.types import InterpolationRequest

        request = InterpolationRequest(
            frame_a=_asset_from_params(params["frame_a"]),
            frame_b=_asset_from_params(params["frame_b"]),
            extra=params.get("extra", {}),
        )
        result = await self._backend.interpolate(request)
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


__all__ = ["InterpolationTask"]
