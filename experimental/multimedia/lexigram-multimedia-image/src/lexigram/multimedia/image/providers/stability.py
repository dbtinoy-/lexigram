"""Stability AI image generation backend."""

from __future__ import annotations

import base64
import binascii
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import aiohttp

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.types import ImageRequest, MediaAsset
from lexigram.multimedia.image.exceptions import (
    ImageGenerationAuthenticationError,
    ImageGenerationError,
)

if TYPE_CHECKING:
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )

_BASE_URL = "https://api.stability.ai"
_DEFAULT_REFERENCE_STRENGTH = 0.65


class StabilityImageProvider:
    """Calls the Stability AI stable-image generation API.

    The API returns base64-encoded image bytes in the response body —
    they are decoded before constructing the MediaAsset.
    """

    def __init__(
        self,
        api_key: str,
        timeout: float = 60.0,
        retry: RetryPolicyProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
    ) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._retry = retry
        self._circuit_breaker = circuit_breaker

    async def _dispatch(
        self, fn: Callable[..., Awaitable[tuple[int, bytes]]], *args: Any
    ) -> tuple[int, bytes]:
        if self._retry is not None and self._circuit_breaker is not None:
            result: tuple[int, bytes] = await self._retry.execute(
                self._circuit_breaker.call, fn, *args
            )
        elif self._retry is not None:
            result = await self._retry.execute(fn, *args)
        elif self._circuit_breaker is not None:
            result = await self._circuit_breaker.call(fn, *args)
        else:
            result = await fn(*args)
        return result

    async def _post(self, payload: dict[str, object]) -> tuple[int, bytes]:
        url = f"{_BASE_URL}/v2beta/stable-image/generate/sd3"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as session,
            session.post(url, json=payload, headers=headers) as resp,
        ):
            if resp.status != 200:
                text = await resp.text()
                return resp.status, text.encode()
            return resp.status, await resp.read()

    async def _post_image_to_image(
        self, request: ImageRequest, strength: float
    ) -> tuple[int, bytes]:
        url = f"{_BASE_URL}/v2beta/stable-image/generate/sd3"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }
        form = aiohttp.FormData()
        form.add_field("prompt", request.prompt)
        form.add_field("mode", "image-to-image")
        form.add_field("strength", str(strength))
        form.add_field("output_format", request.format)
        mime_type = request.reference_mime_type or "image/png"
        form.add_field(
            "image",
            request.reference_image,
            filename=f"reference.{mime_type.split('/')[-1]}",
            content_type=mime_type,
        )
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as session,
            session.post(url, data=form, headers=headers) as resp,
        ):
            if resp.status != 200:
                text = await resp.text()
                return resp.status, text.encode()
            return resp.status, await resp.read()

    async def generate(
        self, request: ImageRequest
    ) -> Result[MediaAsset, ImageGenerationError]:
        try:
            if request.reference_image is not None:
                strength = float(
                    request.extra.get("reference_strength", _DEFAULT_REFERENCE_STRENGTH)
                )
                status, body = await self._dispatch(
                    self._post_image_to_image, request, strength
                )
            else:
                payload: dict[str, object] = {
                    "prompt": request.prompt,
                    "width": request.width,
                    "height": request.height,
                    "format": request.format,
                }
                status, body = await self._dispatch(self._post, payload)
        except (aiohttp.ClientError, TimeoutError) as exc:
            return Err(
                ImageGenerationError(f"Stability request failed: {exc}", cause=exc)
            )

        if status == 401:
            return Err(
                ImageGenerationAuthenticationError("Stability AI rejected the API key")
            )
        if status != 200:
            return Err(ImageGenerationError(f"Stability returned {status}: {body!r}"))

        try:
            image_bytes = base64.b64decode(body)
        except (ValueError, binascii.Error) as exc:
            return Err(
                ImageGenerationError(
                    "Stability returned invalid base64 image data", cause=exc
                )
            )
        return Ok(
            MediaAsset(
                mime_type=f"image/{request.format}",
                provider="stability",
                bytes_data=image_bytes,
            )
        )


__all__ = ["StabilityImageProvider"]
