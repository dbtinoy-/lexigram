"""Local self-hosted video generation server backend."""

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

class LocalHttpVideoProvider:
    """Talks to a self-hosted video generation HTTP server.

    No SDK dependency — this is the always-available zero-extra backend.
    Video servers commonly respond with either the raw media bytes or a
    JSON body of the form ``{"url": "..."}`` (files are too large to
    ship inline) — both response shapes are supported.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 60.0,
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
            return Err(
                VideoGenerationError(
                    f"local-http video request failed: {exc}", cause=exc
                )
            )

        if status != 200:
            return Err(
                VideoGenerationError(
                    f"local-http video server returned {status}: {body!r}"
                )
            )

        if content_type.startswith("application/json"):
            return self._asset_from_json(body, content_type)

        return Ok(
            MediaAsset(
                mime_type=content_type,
                provider="local-http",
                bytes_data=body,
            )
        )

    def _asset_from_json(
        self, body: bytes, content_type: str
    ) -> Result[MediaAsset, VideoGenerationError]:
        try:
            data = loads_str(body.decode("utf-8"))
        except JSONDecodeError as exc:
            return Err(
                VideoGenerationError(
                    f"local-http video server returned invalid JSON: {body!r}",
                    cause=exc,
                )
            )
        if not isinstance(data, dict):
            return Err(
                VideoGenerationError(
                    f"local-http video server returned non-object JSON: {body!r}"
                )
            )
        url = data.get("url")
        if not isinstance(url, str) or not url:
            return Err(
                VideoGenerationError(
                    f"local-http video server JSON missing url: {body!r}"
                )
            )
        return Ok(
            MediaAsset(
                mime_type="video/mp4",
                provider="local-http",
                uri=url,
            )
        )


__all__ = ["LocalHttpVideoProvider"]
