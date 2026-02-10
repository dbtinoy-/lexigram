"""OpenAI (DALL-E) image generation backend."""

from __future__ import annotations

import base64
import binascii
from typing import TYPE_CHECKING

import aiohttp

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.types import ImageRequest, MediaAsset
from lexigram.multimedia.image.exceptions import (
    ImageGenerationAuthenticationError,
    ImageGenerationError,
)
from lexigram.serialization import loads

if TYPE_CHECKING:
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )

_SUPPORTED_SIZES: dict[str, set[str]] = {
    "dall-e-3": {"1024x1024", "1024x1792", "1792x1024"},
    "dall-e-2": {"256x256", "512x512", "1024x1024"},
}


class OpenAIImageProvider:
    """Calls the OpenAI (or an OpenAI-compatible-gateway) Images API.

    ``base_url`` is configurable rather than hardcoded to api.openai.com so
    this can point at a self-hosted or third-party gateway that speaks the
    same /v1/images/generations wire shape behind a different model,
    including non-OpenAI models routed through a compatible gateway.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "dall-e-3",
        base_url: str = "https://api.openai.com",
        timeout: float = 60.0,
        retry: RetryPolicyProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._retry = retry
        self._circuit_breaker = circuit_breaker

    async def _post(self, payload: dict[str, object]) -> tuple[int, bytes]:
        url = f"{self._base_url}/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as session,
            session.post(url, json=payload, headers=headers) as resp,
        ):
            return resp.status, await resp.read()

    async def generate(
        self, request: ImageRequest
    ) -> Result[MediaAsset, ImageGenerationError]:
        size = f"{request.width}x{request.height}"
        supported = _SUPPORTED_SIZES.get(self._model)
        if supported is not None and size not in supported:
            return Err(
                ImageGenerationError(
                    f"{self._model} does not support size {size!r}; "
                    f"supported sizes: {sorted(supported)}"
                )
            )

        payload: dict[str, object] = {
            "model": self._model,
            "prompt": request.prompt,
            "size": size,
            "response_format": "b64_json",
        }
        try:
            if self._retry is not None and self._circuit_breaker is not None:
                status, body = await self._retry.execute(
                    self._circuit_breaker.call, self._post, payload
                )
            elif self._retry is not None:
                status, body = await self._retry.execute(self._post, payload)
            elif self._circuit_breaker is not None:
                status, body = await self._circuit_breaker.call(self._post, payload)
            else:
                status, body = await self._post(payload)
        except (aiohttp.ClientError, TimeoutError) as exc:
            return Err(ImageGenerationError(f"OpenAI request failed: {exc}", cause=exc))

        if status == 401:
            return Err(
                ImageGenerationAuthenticationError("OpenAI rejected the API key")
            )
        if status != 200:
            return Err(ImageGenerationError(f"OpenAI returned {status}: {body!r}"))

        try:
            parsed = loads(body)
            b64_data = parsed["data"][0]["b64_json"]
            image_bytes = base64.b64decode(b64_data)
        except (ValueError, KeyError, IndexError, TypeError, binascii.Error) as exc:
            return Err(
                ImageGenerationError(
                    "OpenAI returned an unparseable or invalid image response",
                    cause=exc,
                )
            )

        return Ok(
            MediaAsset(
                mime_type=f"image/{request.format}",
                provider="openai",
                bytes_data=image_bytes,
            )
        )


__all__ = ["OpenAIImageProvider"]
