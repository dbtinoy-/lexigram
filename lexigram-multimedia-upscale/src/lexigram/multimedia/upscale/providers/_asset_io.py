"""Shared source-bytes resolution for upscale providers."""

from __future__ import annotations

import aiohttp

from lexigram.contracts.multimedia.security import (
    DEFAULT_MAX_MEDIA_BYTES,
    asset_bytes_ok,
)
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.contracts.security.url_safety import (
    HostResolver,
    is_safe_url_for_request,
)
from lexigram.multimedia.upscale.exceptions import (
    UpscaleAssetDownloadError,
    UpscaleAssetTooLargeError,
    UpscaleUnsafeAssetURLError,
)


async def resolve_asset_bytes(
    asset: MediaAsset,
    *,
    max_bytes: int = DEFAULT_MAX_MEDIA_BYTES,
    resolver: HostResolver | None = None,
) -> bytes:
    """Resolve an asset's source bytes, enforcing size and URL-safety policy.

    Inline bytes are returned as-is when they fit under ``max_bytes``.
    Remote URIs are validated against the SSRF primitive
    (``is_safe_url_for_request``) and streamed with a hard byte cap;
    redirects are never followed.

    Args:
        asset: Source media asset (inline bytes or remote URI).
        max_bytes: Maximum accepted payload size in bytes. Defaults to
            the framework media cap.
        resolver: Optional hostname resolver for the URL-safety check.
            Defaults to the system resolver.

    Returns:
        The asset's bytes when they satisfy the size and URL policy.

    Raises:
        UpscaleAssetDownloadError: If the remote fetch returns a non-200
            response.
        UpscaleAssetTooLargeError: If the payload exceeds ``max_bytes``.
        UpscaleUnsafeAssetURLError: If the URI is missing or not safe to
            request.
    """
    if asset.has_bytes:
        if not asset_bytes_ok(len(asset.bytes_data or b""), max_bytes=max_bytes):
            raise UpscaleAssetTooLargeError(max_bytes)
        return asset.bytes_data or b""
    uri = asset.uri
    if not uri or not is_safe_url_for_request(uri, resolver=resolver):
        raise UpscaleUnsafeAssetURLError(uri or "")
    async with (
        aiohttp.ClientSession() as session,
        session.get(uri, allow_redirects=False) as resp,
    ):
        if resp.status != 200:
            raise UpscaleAssetDownloadError(resp.status)
        declared = resp.content_length
        if declared is not None and not asset_bytes_ok(declared, max_bytes=max_bytes):
            raise UpscaleAssetTooLargeError(max_bytes)
        chunks = []
        total = 0
        async for chunk in resp.content.iter_chunked(64 * 1024):
            total += len(chunk)
            if not asset_bytes_ok(total, max_bytes=max_bytes):
                raise UpscaleAssetTooLargeError(max_bytes)
            chunks.append(chunk)
        return b"".join(chunks)


__all__ = ["resolve_asset_bytes"]
