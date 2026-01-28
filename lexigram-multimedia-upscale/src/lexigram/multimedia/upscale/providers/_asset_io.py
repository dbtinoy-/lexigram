"""Shared source-bytes resolution for upscale providers."""

from __future__ import annotations

import aiohttp

from lexigram.contracts.multimedia.types import MediaAsset


async def resolve_asset_bytes(asset: MediaAsset) -> bytes:
    if asset.has_bytes:
        return asset.bytes_data or b""
    async with (
        aiohttp.ClientSession() as session,
        session.get(asset.uri) as resp,  # type: ignore[arg-type]
    ):
        return await resp.read()


__all__ = ["resolve_asset_bytes"]
