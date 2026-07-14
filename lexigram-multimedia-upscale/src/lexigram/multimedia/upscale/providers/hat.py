"""HAT (Hybrid Attention Transformer) local super-resolution reference-server client."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

import aiohttp

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.exceptions import UpscaleError
from lexigram.contracts.multimedia.types import MediaAsset, UpscaleRequest
from lexigram.multimedia.upscale.providers._asset_io import resolve_asset_bytes

if TYPE_CHECKING:
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )


class HatUpscaleProvider:
    """Talks to a hat_server.py reference server via UpscaleProvider."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
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
            session.post(f"{self._base_url}/upscale", json=payload) as resp,
        ):
            if resp.status != 200:
                text = await resp.text()
                return resp.status, text.encode(), ""
            body = await resp.read()
            content_type = resp.headers.get("Content-Type", "image/png")
            return resp.status, body, content_type

    async def upscale(
        self, request: UpscaleRequest
    ) -> Result[MediaAsset, UpscaleError]:
        try:
            image_bytes = await resolve_asset_bytes(request.asset)
        except (UpscaleError, ValueError) as exc:
            return Err(UpscaleError(str(exc)))
        payload: dict[str, object] = {
            "image_bytes": base64.b64encode(image_bytes).decode("ascii"),
            "scale_factor": request.scale_factor,
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
            return Err(UpscaleError(f"HAT request failed: {exc}", cause=exc))

        if status != 200:
            return Err(UpscaleError(f"HAT server returned {status}: {body!r}"))

        return Ok(MediaAsset(mime_type=content_type, provider="hat", bytes_data=body))


__all__ = ["HatUpscaleProvider"]
