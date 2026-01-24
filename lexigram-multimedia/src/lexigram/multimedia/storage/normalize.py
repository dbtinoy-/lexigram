"""Normalize MediaAssets across the input/output boundary.

Input side (submission): upload bytes-carrying MediaAssets to blob storage
before task submission — mirrors normalize_asset_dict's output-side
normalization but operates on VideoOperation/Timeline dataclasses instead of
output dicts, so task payloads stay small enough to cross the task-queue
boundary.

Output side (results): normalizes a MediaAsset-shaped dict to always carry a
URI before it reaches lexigram-tasks' JSON-serializing result store. Checks
the asset's actual shape (bytes vs URI), not the provider category —
ElevenLabs, OpenAI TTS, Stability, and local/in-process backends all return
bytes; Runway and local video/image servers may return either. See design
spec 'Async job model & error handling'.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

from lexigram.contracts.multimedia.types import (
    ComposeVideo,
    MediaAsset,
    VideoOperation,
)

if TYPE_CHECKING:
    from lexigram.contracts.infra.storage.protocols import BlobStoreProtocol


async def _upload_if_bytes(
    asset: MediaAsset, *, storage: Any, path_prefix: str
) -> MediaAsset:
    if not asset.has_bytes:
        return asset
    import uuid

    file_info = await storage.upload(
        path=f"{path_prefix}{uuid.uuid4().hex}",
        data=asset.bytes_data,
        content_type=asset.mime_type,
    )
    url = await storage.get_url(file_info.path)
    return dataclasses.replace(asset, bytes_data=None, uri=url)


async def normalize_operation_assets(
    operation: VideoOperation, *, storage: Any, path_prefix: str
) -> VideoOperation:
    if storage is None:
        return operation

    if isinstance(operation, ComposeVideo):
        new_asset = await _upload_if_bytes(
            operation.asset, storage=storage, path_prefix=path_prefix
        )
        new_layers = [
            dataclasses.replace(
                layer,
                asset=await _upload_if_bytes(
                    layer.asset, storage=storage, path_prefix=path_prefix
                ),
            )
            for layer in operation.layers
        ]
        new_audio_layers = [
            dataclasses.replace(
                layer,
                asset=await _upload_if_bytes(
                    layer.asset, storage=storage, path_prefix=path_prefix
                ),
            )
            for layer in operation.audio_layers
        ]
        if (
            new_asset is operation.asset
            and new_layers == operation.layers
            and new_audio_layers == operation.audio_layers
        ):
            return operation
        return dataclasses.replace(
            operation,
            asset=new_asset,
            layers=new_layers,
            audio_layers=new_audio_layers,
        )

    fields = dataclasses.fields(operation)
    updates: dict[str, Any] = {}
    changed = False

    for f in fields:
        value = getattr(operation, f.name)
        if isinstance(value, MediaAsset):
            new_value = await _upload_if_bytes(
                value, storage=storage, path_prefix=path_prefix
            )
            if new_value is not value:
                updates[f.name] = new_value
                changed = True
        elif isinstance(value, list) and value and isinstance(value[0], MediaAsset):
            new_list = [
                await _upload_if_bytes(a, storage=storage, path_prefix=path_prefix)
                for a in value
            ]
            if new_list != value:
                updates[f.name] = new_list
                changed = True

    if not changed:
        return operation
    return dataclasses.replace(operation, **updates)


async def normalize_timeline_assets(
    timeline: Any, *, storage: Any, path_prefix: str
) -> Any:
    if storage is None:
        return timeline

    from lexigram.multimedia.timeline import Timeline

    normalized = Timeline()
    transitions = timeline.transitions
    for i, clip in enumerate(timeline.clips):
        # add_clip()'s transition_in describes the transition joining this
        # clip to the previous one, so it only applies from the second clip
        # onward — mirrors Timeline.from_params()'s own indexing. Without
        # this, every rebuilt clip would default to a hard cut and silently
        # discard whatever transitions the caller configured.
        transition_in = (
            transitions[i - 1] if i > 0 and i - 1 < len(transitions) else None
        )
        normalized.add_clip(
            await _upload_if_bytes(clip, storage=storage, path_prefix=path_prefix),
            transition_in=transition_in,
        )
    if timeline.narration is not None:
        normalized.set_narration(
            await _upload_if_bytes(
                timeline.narration, storage=storage, path_prefix=path_prefix
            )
        )
    if timeline.music is not None:
        normalized.set_music(
            await _upload_if_bytes(
                timeline.music, storage=storage, path_prefix=path_prefix
            ),
            duck_under_narration=timeline.duck_under_narration,
        )
    if timeline.captions:
        normalized.add_captions(timeline.captions)
    for layer in timeline.overlays:
        normalized.add_overlay(
            await _upload_if_bytes(
                layer.asset, storage=storage, path_prefix=path_prefix
            ),
            start=layer.start,
            end=layer.end,
            fade_in=layer.fade_in,
            fade_out=layer.fade_out,
        )
    for audio in timeline.audio_layers:
        normalized.add_audio(
            await _upload_if_bytes(
                audio.asset, storage=storage, path_prefix=path_prefix
            ),
            start=audio.start,
            volume=audio.volume,
        )
    if timeline.fade_in:
        normalized.set_fade_in(timeline.fade_in)
    if timeline.fade_out:
        normalized.set_fade_out(timeline.fade_out)
    if timeline.base_fade_out:
        normalized.set_base_fade_out(timeline.base_fade_out)
    if timeline.encode is not None:
        normalized.set_encode(timeline.encode)
    return normalized


async def normalize_asset_dict(
    asset_dict: dict[str, Any],
    *,
    store: BlobStoreProtocol,
    path_prefix: str,
    path_key: str,
) -> dict[str, Any]:
    if asset_dict.get("bytes_data") is None:
        return asset_dict

    path = f"{path_prefix}{path_key}"
    await store.upload(
        path,
        data=asset_dict["bytes_data"],
        content_type=asset_dict.get("mime_type"),
    )
    url = await store.get_url(path)

    return {**asset_dict, "bytes_data": None, "uri": url}


__all__ = [
    "normalize_asset_dict",
    "normalize_operation_assets",
    "normalize_timeline_assets",
]
