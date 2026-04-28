"""OpenAI-compatible video generation gateway backend.

``base_url``/``model`` are both configurable and free-form — this
provider exists to serve gateway-routed models (e.g. a third-party
gateway routing Seedance/other vendor models through one OpenAI-style
endpoint) that speak one shared submit+poll wire shape behind a model
name, not to hit one specific hardcoded vendor. The exact endpoint path
and response shape below are illustrative — confirm against the actual
target API before relying on this in production (design spec §11.5).

Uses raw aiohttp, not the openai PyPI SDK, matching every other cloud
provider in this codebase (design spec §6.5). Reuses RunwayVideoProvider's
internal submit+poll structure (design spec §4.3) — a distinct class,
not a subclass, since the two vendors' request/response JSON shapes
differ and there is no shared base class for cloud video providers.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import aiohttp

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.types import MediaAsset, VideoRequest
from lexigram.multimedia.video.exceptions import (
    VideoGenerationAuthenticationError,
    VideoGenerationError,
    VideoTimeoutError,
)
from lexigram.serialization import JSONDecodeError, loads_str

if TYPE_CHECKING:
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )


class OpenAIVideoProvider:
    """Talks to an OpenAI-compatible video-generation gateway."""

    def __init__(
        self,
        api_key: str,
        model: str = "sora-2",
        base_url: str = "https://api.openai.com",
        timeout: float = 60.0,
        poll_interval: float = 3.0,
        max_polls: int = 60,
        retry: RetryPolicyProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._poll_interval = poll_interval
        self._max_polls = max_polls
        self._retry = retry
        self._circuit_breaker = circuit_breaker

    async def generate(
        self, request: VideoRequest
    ) -> Result[MediaAsset, VideoGenerationError]:
        payload: dict[str, object] = {
            "model": self._model,
            "prompt": request.prompt,
            "seconds": request.duration_seconds,
            "size": request.resolution,
        }
        try:
            video_id = await self._submit(payload)
        except (aiohttp.ClientError, TimeoutError) as exc:
            return Err(
                VideoGenerationError(f"OpenAI video request failed: {exc}", cause=exc)
            )
        except VideoGenerationError as exc:
            return Err(exc)

        try:
            output_url = await self._poll_until_done(video_id)
        except (aiohttp.ClientError, TimeoutError) as exc:
            return Err(
                VideoGenerationError(f"OpenAI video request failed: {exc}", cause=exc)
            )
        except VideoGenerationError as exc:
            return Err(exc)

        if output_url is None:
            return Err(
                VideoTimeoutError(
                    "OpenAI video generation did not complete within the poll budget"
                )
            )

        return Ok(MediaAsset(mime_type="video/mp4", provider="openai", uri=output_url))

    async def _submit(self, payload: dict[str, object]) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as session,
            session.post(
                f"{self._base_url}/v1/videos", json=payload, headers=headers
            ) as resp,
        ):
            body = await resp.text()
        if resp.status == 401:
            raise VideoGenerationAuthenticationError("OpenAI rejected the API key")
        if resp.status != 200:
            raise VideoGenerationError(
                f"OpenAI video submit returned {resp.status}: {body!r}"
            )
        try:
            data = loads_str(body)
        except JSONDecodeError as exc:
            raise VideoGenerationError(
                f"OpenAI video submit returned invalid JSON: {body!r}", cause=exc
            ) from exc
        if not isinstance(data, dict):
            raise VideoGenerationError(
                f"OpenAI video submit response missing id: {body!r}"
            )
        video_id = data.get("id")
        if not isinstance(video_id, str):
            raise VideoGenerationError(
                f"OpenAI video submit response missing id: {body!r}"
            )
        return video_id

    async def _poll_until_done(self, video_id: str) -> str | None:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        for _ in range(self._max_polls):
            await asyncio.sleep(self._poll_interval)
            async with (
                aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self._timeout)
                ) as session,
                session.get(
                    f"{self._base_url}/v1/videos/{video_id}", headers=headers
                ) as resp,
            ):
                body = await resp.text()
            if resp.status == 401:
                raise VideoGenerationAuthenticationError("OpenAI rejected the API key")
            if resp.status != 200:
                raise VideoGenerationError(
                    f"OpenAI video poll returned {resp.status}: {body!r}"
                )
            status, output_url = self._parse_poll(body)
            if status == "failed":
                raise VideoGenerationError(f"OpenAI video {video_id} failed: {body!r}")
            if status == "completed":
                if output_url is None:
                    raise VideoGenerationError(
                        f"OpenAI video {video_id} completed without a url: {body!r}"
                    )
                return output_url
        return None

    def _parse_poll(self, body: str) -> tuple[str | None, str | None]:
        try:
            data: dict[str, Any] = loads_str(body)
        except JSONDecodeError:
            return None, None
        status = data.get("status")
        if not isinstance(status, str):
            return None, None
        url = data.get("url")
        return status, url if isinstance(url, str) else None


__all__ = ["OpenAIVideoProvider"]
