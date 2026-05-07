"""OpenAI-compatible video generation gateway backend.

``base_url``/``model`` are both configurable and free-form — this
provider exists to serve gateway-routed models (e.g. a third-party
gateway routing Seedance/other vendor models through one OpenAI-style
endpoint) that speak one shared submit+poll wire shape behind a model
name, not to hit one specific hardcoded vendor. The payload keys follow
the Seedance/HuiMeng gateway contract (``duration``, ``image_url``,
``first_frame_image``, ``last_frame_image``, ``reference_images``,
``reference_videos``, ``reference_audios``, ``generate_audio``,
``return_last_frame``, ``ratio``, ``seed``) — the exact endpoint path
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
from lexigram.contracts.multimedia.types import MediaAsset, VideoMode, VideoRequest
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
        try:
            payload = self._build_payload(request)
        except VideoGenerationError as exc:
            return Err(exc)
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

    def _build_payload(self, request: VideoRequest) -> dict[str, object]:
        """Build the gateway payload for a request.

        `request.model` overrides the provider's config-level model. Frame and
        reference keys use the Seedance/HuiMeng gateway names; optional keys
        are only emitted when explicitly set (non-default), keeping the
        payload backward-compatible with plain OpenAI-style endpoints.
        """
        payload: dict[str, object] = {
            "model": request.model or self._model,
            "prompt": request.prompt,
            "duration": int(request.duration_seconds),
            "resolution": request.resolution,
        }
        if request.ratio:
            payload["ratio"] = request.ratio

        mode = request.mode or self._derive_mode(request)
        if mode == VideoMode.TEXT_TO_VIDEO:
            return payload
        if mode == VideoMode.FIRST_FRAME:
            if not request.image_uri:
                raise VideoGenerationError("first_frame mode requires image_uri")
            payload["image_url"] = request.image_uri
        elif mode == VideoMode.FIRST_LAST_FRAME:
            if not request.image_uri or not request.last_frame_image:
                raise VideoGenerationError(
                    "first_last_frame mode requires image_uri and last_frame_image"
                )
            payload["first_frame_image"] = request.image_uri
            payload["last_frame_image"] = request.last_frame_image
        else:  # MULTIMODAL_REFERENCE
            images = [uri for uri in request.reference_images if uri]
            videos = [uri for uri in request.reference_videos if uri]
            audios = [uri for uri in request.reference_audios if uri]
            if not images and not videos:
                raise VideoGenerationError(
                    "multimodal_reference mode requires reference_images or reference_videos"
                )
            if len(images) > 9:
                raise VideoGenerationError(
                    "multimodal_reference mode supports at most 9 reference_images"
                )
            if len(videos) > 3:
                raise VideoGenerationError(
                    "multimodal_reference mode supports at most 3 reference_videos"
                )
            if len(audios) > 3:
                raise VideoGenerationError(
                    "multimodal_reference mode supports at most 3 reference_audios"
                )
            if images:
                payload["reference_images"] = images
            if videos:
                payload["reference_videos"] = videos
            if audios:
                payload["reference_audios"] = audios

        if request.generate_audio:
            payload["generate_audio"] = True
        if request.return_last_frame:
            payload["return_last_frame"] = True
        if request.seed is not None:
            payload["seed"] = request.seed
        return payload

    @staticmethod
    def _derive_mode(request: VideoRequest) -> VideoMode:
        """Derive the reference-input mode from which fields are set."""
        if request.reference_images or request.reference_videos:
            return VideoMode.MULTIMODAL_REFERENCE
        if request.last_frame_image:
            return VideoMode.FIRST_LAST_FRAME
        if request.image_uri:
            return VideoMode.FIRST_FRAME
        return VideoMode.TEXT_TO_VIDEO

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
