"""Normalizes a MediaAsset-shaped dict to always carry a URI before it
reaches lexigram-tasks' JSON-serializing result store.

Checks the asset's actual shape (bytes vs URI), not the provider category —
ElevenLabs, OpenAI TTS, Stability, and local/in-process backends all return
bytes; Runway and local video/image servers may return either. See design
spec 'Async job model & error handling'.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.infra.storage.protocols import BlobStoreProtocol


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


__all__ = ["normalize_asset_dict"]
