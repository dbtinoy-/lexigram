"""ComfyUI local video generation backend.

ComfyUI is treated as an already-running, already-loaded persistent
server — a thin HTTP client against its existing submit/poll/fetch API,
mirroring ComfyUiImageProvider's architecture (design spec §4.2).
Positioned as a secondary/optional backend — the config default stays
local-http; the three reference-server engines (Wan2.2, CogVideoX, SVD)
are the primary local path (design spec §2, goal 2).
"""

from __future__ import annotations

import asyncio
import importlib.resources
import random
from typing import TYPE_CHECKING, Any
import uuid

import aiohttp

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.types import MediaAsset, VideoRequest
from lexigram.multimedia.video.exceptions import VideoGenerationError, VideoTimeoutError
from lexigram.serialization import dumps_str, loads

if TYPE_CHECKING:
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )


def _load_default_workflow() -> dict[str, Any]:
    template_path = importlib.resources.files(
        "lexigram.multimedia.video.workflows"
    ).joinpath("default_svd.json")
    workflow: dict[str, Any] = loads(template_path.read_text())
    return workflow


def _fill_workflow(
    template: dict[str, Any],
    *,
    image_path: str,
    checkpoint: str,
    fps: int,
    motion_bucket_id: int,
    seed: int,
) -> dict[str, Any]:
    raw = dumps_str(template)
    raw = raw.replace('"__IMAGE_PATH__"', dumps_str(image_path))
    raw = raw.replace('"__CHECKPOINT__"', dumps_str(checkpoint))
    raw = raw.replace('"__FPS__"', str(fps))
    raw = raw.replace('"__MOTION_BUCKET_ID__"', str(motion_bucket_id))
    raw = raw.replace('"__SEED__"', str(seed))
    filled: dict[str, Any] = loads(raw)
    return filled


class ComfyUiVideoProvider:
    """Submits a filled-in SVD workflow to ComfyUI, polls history, fetches output.

    Requires request.image_uri — the bundled default workflow targets
    SVD-style image-to-video graphs (design spec §11.4). image_uri is
    assumed to already be a path reachable by the ComfyUI process, the
    same locally-reachable trust boundary the design assumes for
    base_url itself (design spec §3 non-goals).
    """

    def __init__(
        self,
        base_url: str,
        checkpoint: str,
        workflow_path: str | None = None,
        fps: int = 6,
        motion_bucket_id: int = 127,
        poll_interval: float = 1.0,
        timeout: float = 120.0,
        retry: RetryPolicyProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._checkpoint = checkpoint
        self._workflow_path = workflow_path
        self._fps = fps
        self._motion_bucket_id = motion_bucket_id
        self._poll_interval = poll_interval
        self._timeout = timeout
        self._retry = retry
        self._circuit_breaker = circuit_breaker

    def _load_template(self) -> dict[str, Any]:
        if self._workflow_path is not None:
            with open(self._workflow_path) as f:
                template: dict[str, Any] = loads(f.read())
                return template
        return _load_default_workflow()

    async def _submit(self, workflow: dict[str, Any]) -> tuple[int, bytes]:
        payload = {"prompt": workflow, "client_id": str(uuid.uuid4())}
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as session,
            session.post(f"{self._base_url}/prompt", json=payload) as resp,
        ):
            return resp.status, await resp.read()

    async def _fetch(
        self, filename: str, subfolder: str, file_type: str
    ) -> tuple[int, bytes]:
        params = {"filename": filename, "subfolder": subfolder, "type": file_type}
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as session,
            session.get(f"{self._base_url}/view", params=params) as resp,
        ):
            return resp.status, await resp.read()

    @staticmethod
    def _has_execution_error(status: dict[str, Any]) -> bool:
        """ComfyUI reports some failures only via status["messages"], a list
        of [event_type, data] pairs, without ever setting status_str to
        "error" — both signals must be checked to fail fast (mirrors
        ComfyUiImageProvider, design spec §4.2).
        """
        messages = status.get("messages", [])
        return any(
            isinstance(m, (list, tuple)) and len(m) > 0 and m[0] == "execution_error"
            for m in messages
        )

    @staticmethod
    def _extract_output_file(entry: dict[str, Any]) -> dict[str, Any]:
        """ComfyUI video-output nodes vary by custom-node family (VHS'
        gifs/videos keys vs. a plain images key) — check each in turn
        rather than assuming one (design spec §11.4).
        """
        for output in entry["outputs"].values():
            for key in ("gifs", "videos", "images"):
                files = output.get(key)
                if files:
                    first_file: dict[str, Any] = files[0]
                    return first_file
        raise KeyError(f"no output file found in ComfyUI history entry: {entry!r}")

    async def _poll_history(
        self, prompt_id: str
    ) -> Result[dict[str, Any], VideoGenerationError]:
        elapsed = 0.0
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self._timeout)
        ) as session:
            while elapsed < self._timeout:
                async with session.get(f"{self._base_url}/history/{prompt_id}") as resp:
                    body = loads(await resp.read())

                entry = body.get(prompt_id)
                if entry is not None:
                    status = entry.get("status", {})
                    if status.get("status_str") == "error" or self._has_execution_error(
                        status
                    ):
                        return Err(
                            VideoGenerationError(
                                f"ComfyUI execution failed for prompt {prompt_id}: {status}"
                            )
                        )
                    if status.get("completed") and entry.get("outputs"):
                        return Ok(entry)

                await asyncio.sleep(self._poll_interval)
                elapsed += self._poll_interval

        return Err(
            VideoTimeoutError(f"ComfyUI prompt {prompt_id} did not complete in time")
        )

    async def generate(
        self, request: VideoRequest
    ) -> Result[MediaAsset, VideoGenerationError]:
        if not request.image_uri:
            return Err(
                VideoGenerationError(
                    "ComfyUiVideoProvider requires request.image_uri — the bundled "
                    "workflow targets SVD-style image-to-video graphs"
                )
            )

        template = self._load_template()
        workflow = _fill_workflow(
            template,
            image_path=request.image_uri,
            checkpoint=self._checkpoint,
            fps=self._fps,
            motion_bucket_id=self._motion_bucket_id,
            seed=random.randint(0, 2**32 - 1),
        )

        try:
            if self._retry is not None and self._circuit_breaker is not None:
                status, body = await self._retry.execute(
                    self._circuit_breaker.call, self._submit, workflow
                )
            elif self._retry is not None:
                status, body = await self._retry.execute(self._submit, workflow)
            elif self._circuit_breaker is not None:
                status, body = await self._circuit_breaker.call(self._submit, workflow)
            else:
                status, body = await self._submit(workflow)
        except (aiohttp.ClientError, TimeoutError) as exc:
            return Err(VideoGenerationError(f"ComfyUI submit failed: {exc}", cause=exc))

        if status != 200:
            return Err(
                VideoGenerationError(f"ComfyUI submit returned {status}: {body!r}")
            )

        prompt_id = loads(body)["prompt_id"]

        history_result = await self._poll_history(prompt_id)
        if history_result.is_err():
            return history_result  # type: ignore[return-value]

        entry = history_result.unwrap()
        file_info = self._extract_output_file(entry)

        try:
            if self._retry is not None and self._circuit_breaker is not None:
                fetch_status, video_bytes = await self._retry.execute(
                    self._circuit_breaker.call,
                    self._fetch,
                    file_info["filename"],
                    file_info["subfolder"],
                    file_info["type"],
                )
            elif self._retry is not None:
                fetch_status, video_bytes = await self._retry.execute(
                    self._fetch,
                    file_info["filename"],
                    file_info["subfolder"],
                    file_info["type"],
                )
            elif self._circuit_breaker is not None:
                fetch_status, video_bytes = await self._circuit_breaker.call(
                    self._fetch,
                    file_info["filename"],
                    file_info["subfolder"],
                    file_info["type"],
                )
            else:
                fetch_status, video_bytes = await self._fetch(
                    file_info["filename"], file_info["subfolder"], file_info["type"]
                )
        except (aiohttp.ClientError, TimeoutError) as exc:
            return Err(VideoGenerationError(f"ComfyUI fetch failed: {exc}", cause=exc))

        if fetch_status != 200:
            return Err(
                VideoGenerationError(
                    f"ComfyUI fetch returned {fetch_status}: {video_bytes!r}"
                )
            )

        return Ok(
            MediaAsset(
                mime_type=f"video/{request.format}",
                provider="comfyui",
                bytes_data=video_bytes,
            )
        )


__all__ = ["ComfyUiVideoProvider"]
