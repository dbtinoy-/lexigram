"""Wan2.2 local video generation reference-server client.

Supports both text-to-video (image_uri=None) and image-to-video
(image_uri set) — Wan2.2 handles both natively, unlike SVD (design
spec §6.1). The wire contract extends what LocalHttpVideoProvider
already speaks (design spec §4.1): image_uri is a URI the server
itself resolves, never base64-inlined.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiohttp

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.types import MediaAsset, VideoRequest
from lexigram.multimedia.video.exceptions import VideoGenerationError
from lexigram.serialization import JSONDecodeError, loads_str

if TYPE_CHECKING:
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )


class Wan22VideoProvider:
    """Talks to a wan22_server.py reference server via VideoProvider."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 180.0,
        retry: RetryPolicyProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._retry = retry
        self._circuit_breaker = circuit_breaker

    async def _post(self, payload: dict[str, object]) -> tuple[int, bytes, str]:
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as session,
            session.post(f"{self._base_url}/generate", json=payload) as resp,
        ):
            if resp.status != 200:
                text = await resp.text()
                return resp.status, text.encode(), ""
            body = await resp.read()
            content_type = resp.headers.get("Content-Type", "video/mp4")
            return resp.status, body, content_type

    async def generate(
        self, request: VideoRequest
    ) -> Result[MediaAsset, VideoGenerationError]:
        payload: dict[str, object] = {
            "prompt": request.prompt,
            "duration_seconds": request.duration_seconds,
            "resolution": request.resolution,
            "image_uri": request.image_uri,
            "format": request.format,
        }
        try:
            if self._retry is not None and self._circuit_breaker is not None:
                status, body, content_type = await self._retry.execute(
                    self._circuit_breaker.call, self._post, payload
                )
            elif self._retry is not None:
                status, body, content_type = await self._retry.execute(
                    self._post, payload
                )
            elif self._circuit_breaker is not None:
                status, body, content_type = await self._circuit_breaker.call(
                    self._post, payload
                )
            else:
                status, body, content_type = await self._post(payload)
        except (aiohttp.ClientError, TimeoutError) as exc:
            return Err(VideoGenerationError(f"Wan2.2 request failed: {exc}", cause=exc))

        if status != 200:
            return Err(
                VideoGenerationError(f"Wan2.2 server returned {status}: {body!r}")
            )

        if content_type.startswith("application/json"):
            return self._asset_from_json(body)

        return Ok(MediaAsset(mime_type=content_type, provider="wan22", bytes_data=body))

    def _asset_from_json(self, body: bytes) -> Result[MediaAsset, VideoGenerationError]:
        try:
            data = loads_str(body.decode("utf-8"))
        except JSONDecodeError as exc:
            return Err(
                VideoGenerationError(
                    f"Wan2.2 server returned invalid JSON: {body!r}", cause=exc
                )
            )
        if not isinstance(data, dict):
            return Err(
                VideoGenerationError(
                    f"Wan2.2 server returned non-object JSON: {body!r}"
                )
            )
        url = data.get("url")
        if not isinstance(url, str) or not url:
            return Err(
                VideoGenerationError(f"Wan2.2 server JSON missing url: {body!r}")
            )
        return Ok(MediaAsset(mime_type="video/mp4", provider="wan22", uri=url))


__all__ = ["Wan22VideoProvider"]
