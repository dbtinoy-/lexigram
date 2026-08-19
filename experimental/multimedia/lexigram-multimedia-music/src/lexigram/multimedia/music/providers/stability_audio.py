"""Stability AI hosted Stable Audio generation backend.

Calls the Stability AI hosted audio generation API
(``POST /v2beta/audio/stable-audio-2/generation``) with
``multipart/form-data`` and ``Accept: audio/*``, returning raw audio
bytes as a MediaAsset — the cloud-backend counterpart to the local
ACE-Step / Stable Audio Open reference servers, mirroring
StabilityImageProvider's cloud pattern. Model selection and sampling
knobs pass through ``request.extra``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import aiohttp

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.types import MediaAsset, MusicRequest
from lexigram.multimedia.music.exceptions import (
    MusicGenerationAuthenticationError,
    MusicGenerationError,
)

if TYPE_CHECKING:
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )

_BASE_URL = "https://api.stability.ai"
_GENERATION_PATH = "/v2beta/audio/stable-audio-2/generation"

_SUPPORTED_OUTPUT_FORMATS: set[str] = {"mp3", "wav"}

# request.extra key -> API form field name
_EXTRA_FORM_FIELDS: dict[str, str] = {
    "seed": "seed",
    "steps": "steps",
    "cfg_scale": "cfg_scale",
    "model": "model",
}


class StabilityAudioMusicProvider:
    """Generate music via the Stability AI hosted Stable Audio API.

    The API returns the generated audio directly in the response body
    when ``Accept: audio/*`` is set — no base64 decoding needed.

    Example:
        ```python
        provider = StabilityAudioMusicProvider(api_key="sk-...")
        result = await provider.generate(MusicRequest(prompt="lo-fi beats"))
        if result.is_ok():
            asset = result.unwrap()
            print(asset.mime_type, len(asset.bytes_data))
        ```

    Note:
        The model defaults to ``stable-audio-2``; override per request
        with ``extra["model"]`` (e.g. ``stable-audio-2.5``). ``seed``,
        ``steps``, and ``cfg_scale`` also pass through ``extra``.
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
        self, fn: Callable[..., Awaitable[tuple[int, bytes, str]]], *args: Any
    ) -> tuple[int, bytes, str]:
        """Run a callable through the configured retry/circuit-breaker chain."""
        if self._retry is not None and self._circuit_breaker is not None:
            result: tuple[int, bytes, str] = await self._retry.execute(
                self._circuit_breaker.call, fn, *args
            )
        elif self._retry is not None:
            result = await self._retry.execute(fn, *args)
        elif self._circuit_breaker is not None:
            result = await self._circuit_breaker.call(fn, *args)
        else:
            result = await fn(*args)
        return result

    @staticmethod
    def _build_payload(request: MusicRequest) -> dict[str, object]:
        """Build the multipart form payload for a request.

        Args:
            request: The music generation request.

        Returns:
            Flat field mapping: API field name to serializable value.
        """
        payload: dict[str, object] = {
            "prompt": request.prompt,
            "output_format": request.format,
            "duration": request.duration_seconds,
        }
        for extra_key, field in _EXTRA_FORM_FIELDS.items():
            if request.extra.get(extra_key) is not None:
                payload[field] = request.extra[extra_key]
        return payload

    async def _post(self, payload: dict[str, object]) -> tuple[int, bytes, str]:
        url = f"{_BASE_URL}{_GENERATION_PATH}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "audio/*",
        }
        form = aiohttp.FormData()
        for name, value in payload.items():
            form.add_field(name, str(value))
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as session,
            session.post(url, data=form, headers=headers) as resp,
        ):
            if resp.status != 200:
                text = await resp.text()
                return resp.status, text.encode(), ""
            content_type = resp.headers.get("Content-Type", "audio/mpeg")
            return resp.status, await resp.read(), content_type

    async def generate(
        self, request: MusicRequest
    ) -> Result[MediaAsset, MusicGenerationError]:
        if request.format not in _SUPPORTED_OUTPUT_FORMATS:
            return Err(
                MusicGenerationError(
                    "Stability Audio supports only "
                    f"{sorted(_SUPPORTED_OUTPUT_FORMATS)}; got {request.format!r}"
                )
            )

        payload = self._build_payload(request)
        try:
            status, body, content_type = await self._dispatch(self._post, payload)
        except (aiohttp.ClientError, TimeoutError) as exc:
            return Err(
                MusicGenerationError(
                    f"Stability Audio request failed: {exc}", cause=exc
                )
            )

        if status == 401:
            return Err(
                MusicGenerationAuthenticationError("Stability AI rejected the API key")
            )
        if status != 200:
            return Err(
                MusicGenerationError(f"Stability Audio returned {status}: {body!r}")
            )

        return Ok(
            MediaAsset(
                mime_type=content_type, provider="stability-audio", bytes_data=body
            )
        )


__all__ = ["StabilityAudioMusicProvider"]
