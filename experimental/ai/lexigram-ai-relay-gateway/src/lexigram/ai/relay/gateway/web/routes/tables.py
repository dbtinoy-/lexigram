from __future__ import annotations

"""Route tables and path constants for the inbound relay web layer."""

from lexigram.ai.relay.gateway.web.audio_endpoints import (
    AUDIO_ROUTE_TABLE,
    audio_speech_endpoint,
    audio_transcriptions_endpoint,
    audio_translations_endpoint,
)
from lexigram.ai.relay.gateway.web.image_endpoints import IMAGE_ROUTE_TABLE
from lexigram.contracts.ai.relay import RelayFormat

_ROUTE_TABLE: tuple[tuple[str, RelayFormat], ...] = (
    ("/v1/chat/completions", RelayFormat.OPENAI_CHAT),
    ("/v1/responses", RelayFormat.OPENAI_RESPONSES),
    ("/v1/messages", RelayFormat.CLAUDE),
    ("/v1beta/models/{model}:generateContent", RelayFormat.GEMINI),
)
"""Inbound path to wire format ownership per route."""
_PASSTHROUGH_ROUTE_TABLE: tuple[tuple[str, str], ...] = (
    ("/v1/embeddings", "embeddings"),
    ("/v1/rerank", "rerank"),
    ("/v1/moderations", "moderation"),
)
"""Inbound path to endpoint kind for passthrough routes."""
_JOB_ROUTE_TABLE: tuple[tuple[str, str], ...] = (("/v1/videos", "video_generation"),)
"""Inbound submit path to endpoint kind for job-relay routes."""

_JOB_STATUS_PATH = "/v1/videos/{job_id}"
"""Inbound poll path for the registered job-relay endpoint kinds."""
_MODEL_LIST_PATHS: tuple[str, ...] = ("/v1/models", "/v1beta/models")
"""Inbound model-list paths; ``/v1beta/models`` is always Gemini."""
_MODEL_DETAIL_PATHS: tuple[str, ...] = (
    "/v1/models/{model}",
    "/v1beta/models/{model}",
)
"""Inbound model-detail paths; ``/v1beta/models/{model}`` is Gemini."""
MODEL_ROUTE_PATHS: tuple[str, ...] = (
    *_MODEL_LIST_PATHS,
    *_MODEL_DETAIL_PATHS,
)
"""Inbound model-list and detail paths registered by ``build_routes``.

The gemini ``/v1beta/models/{model}:generateContent`` relay path mounts
alongside these without colliding because the detail path is a distinct
pattern.
"""
_AUDIO_HANDLERS = {
    "audio_speech": audio_speech_endpoint,
    "audio_transcriptions": audio_transcriptions_endpoint,
    "audio_translations": audio_translations_endpoint,
}
"""Endpoint kind to handler for the audio passthrough routes."""
RELAY_ROUTE_PATHS: tuple[str, ...] = tuple(
    path
    for path, _ in (
        *_ROUTE_TABLE,
        *_PASSTHROUGH_ROUTE_TABLE,
        *AUDIO_ROUTE_TABLE,
        *IMAGE_ROUTE_TABLE,
    )
)
"""Inbound relay paths registered by ``build_routes``, in route order."""
