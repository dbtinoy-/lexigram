"""Upload bytes-carrying MediaAssets to blob storage before task submission.

Mirrors storage_normalize.py's output-side normalization, but operates on
input VideoOperation/Timeline dataclasses instead of output dicts — assets
with inline bytes get uploaded and swapped for a URI reference so task
payloads stay small enough to cross the task-queue boundary.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from lexigram.contracts.multimedia.types import MediaAsset, VideoOperation


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


__all__ = ["normalize_operation_assets"]
