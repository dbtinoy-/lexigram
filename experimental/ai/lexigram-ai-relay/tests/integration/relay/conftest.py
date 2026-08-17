"""Shared harness for the relaykit golden matrix.

Recognised relaykit-only output (dropped before comparison, tracked as
the closed allowlist below) falls into three categories:

1. **Host billing layer** — ``billing_usage`` is attached by the new-api
   gateway's usage state, not by the converter.  It is a bounded-account
   concern (relay plan C), so the engine never emits it.
2. **Host channel metadata** — ``usage_semantic`` / ``usage_source``
   annotate the usage envelope with gateway channel identity.
3. **relaykit Go-DTO serialization artifacts** — explicit nulls and
   zero-valued cross-family fields that relaykit's Go structs always
   serialize (``system_fingerprint``, ``MimeType``, ``input_tokens_details``,
   ``claude_cache_*``, per-detail ``text_tokens``/``audio_tokens``/
   ``image_tokens``, stream ``logprobs``).  The engine omits None fields
   and never emits cross-family usage keys.

Any divergence outside these documented drops fails the test.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from lexigram.ai.relay import RelayConverterRegistry
from lexigram.contracts.ai.relay.context import (
    GeminiOptions,
    RelayConversionContext,
    RelayOptions,
)
from lexigram.contracts.ai.relay.dto import (
    ClaudeRequest,
    ClaudeResponse,
    GeminiRequest,
    GeminiResponse,
    OpenAIChatRequest,
    OpenAIChatResponse,
    ResponsesRequest,
    ResponsesResponse,
)
from lexigram.contracts.ai.relay.ir import StreamDelta
from lexigram.contracts.ai.relay.types import RelayFormat, RelayUsage
from lexigram.contracts.core.result import Ok

from ._fixtures import FORMAT_SLUGS

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "relay"

REQUEST_DTOS = {
    "openai": OpenAIChatRequest,
    "openai_responses": ResponsesRequest,
    "claude": ClaudeRequest,
    "gemini": GeminiRequest,
}
RESPONSE_DTOS = {
    "openai": OpenAIChatResponse,
    "openai_responses": ResponsesResponse,
    "claude": ClaudeResponse,
    "gemini": GeminiResponse,
}
HEX32 = re.compile(r"[0-9a-f]{32}")
TIMESTAMP = re.compile(r"(\"(?:created|created_at)\"\s*:\s*)\d{9,}")


class _FixedResolver:
    """Reproduces relaykit's ``TestMain`` fixed media resolver."""

    def resolve(self, url: str):
        return Ok(("image/png", "aGVsbG8="))


def golden_context() -> RelayConversionContext:
    """Conversion context mirroring relaykit ``goldenInfo()`` defaults.

    relaykit's ``goldenInfo`` leaves ``SupportsImagine`` unset, so the
    image-generation capability lookup reports ``False`` and no
    ``responseModalities`` are attached.
    """
    return RelayConversionContext(
        media_resolver=_FixedResolver(),
        safety_setting=lambda _category: "OFF",
        supports_image_generation=lambda _model: False,
        preserve_thinking_suffix=lambda _model: False,
        default_max_tokens=lambda _model: None,
        upstream_model="upstream-model",
        options=RelayOptions(
            gemini=GeminiOptions(thought_signature_bypass=True),
        ),
    )


@pytest.fixture(scope="session")
def registry() -> RelayConverterRegistry:
    return RelayConverterRegistry.with_defaults()


@pytest.fixture
def ctx() -> RelayConversionContext:
    return golden_context()


def load_golden(kind: str, route: str) -> Any:
    """Load one golden fixture as parsed JSON."""
    path = FIXTURE_DIR / kind / f"{route}.golden.json"
    return json.loads(path.read_text())


# -- volatility ------------------------------------------------------------

def normalize_volatile(obj: Any) -> Any:
    """Reproduce relaykit ``normalizeVolatile`` on a parsed JSON tree."""
    text = json.dumps(obj, indent=2)
    text = HEX32.sub("<uuid>", text)
    text = TIMESTAMP.sub(r"\g<1>0", text)
    return json.loads(text)


# -- closed allowlist --------------------------------------------------------

USAGE_DROP_KEYS = {
    "input_tokens_details",
    "claude_cache_creation_5_m_tokens",
    "claude_cache_creation_1_h_tokens",
    "usage_semantic",
    "usage_source",
}
USAGE_DETAILS_DROP_KEYS = {"text_tokens", "audio_tokens", "image_tokens"}
DETAIL_CONTAINER_KEYS = {"prompt_tokens_details", "completion_tokens_details"}
ARTIFACT_NULL_KEYS = {"system_fingerprint", "logprobs"}
STREAM_CHOICE_ARTIFACT_KEYS = {"logprobs"}


def drop_relaykit_only(value: Any) -> Any:
    """Remove the documented relaykit host/artifact fields for comparison."""

    def recurse(v: Any) -> Any:
        if isinstance(v, dict):
            out: dict[str, Any] = {}
            for key, item in v.items():
                if key == "billing_usage" or key == "MimeType":
                    continue
                if key in ARTIFACT_NULL_KEYS:
                    continue
                if key in USAGE_DROP_KEYS:
                    continue
                if isinstance(item, dict):
                    if key in USAGE_DETAILS_DROP_KEYS:
                        continue
                    if key in DETAIL_CONTAINER_KEYS:
                        item = {
                            k: sub
                            for k, sub in item.items()
                            if k not in USAGE_DETAILS_DROP_KEYS
                        }
                    out[key] = recurse(item)
                else:
                    out[key] = recurse(item)
            return out
        if isinstance(v, list):
            return [recurse(item) for item in v]
        return v

    return recurse(value)


# -- source stream transcription ----------------------------------------------

def openai_stream_deltas() -> list[StreamDelta]:
    return [
        StreamDelta(kind="role", role="assistant"),
        StreamDelta(kind="content", content="Hello"),
        StreamDelta(kind="content", content=" world"),
        StreamDelta(
            kind="usage",
            usage=RelayUsage(prompt_tokens=4, completion_tokens=2),
        ),
        StreamDelta(kind="finish", finish_reason="stop"),
    ]


def claude_stream_deltas() -> list[StreamDelta]:
    return [
        StreamDelta(
            kind="role",
            role="assistant",
            usage=RelayUsage(prompt_tokens=4, completion_tokens=0),
        ),
        StreamDelta(kind="content", content=""),
        StreamDelta(kind="content", content="Hello world"),
        StreamDelta(
            kind="finish",
            finish_reason="end_turn",
            usage=RelayUsage(prompt_tokens=0, completion_tokens=2),
        ),
    ]


def gemini_stream_deltas() -> list[StreamDelta]:
    return [
        StreamDelta(kind="role", role="model"),
        StreamDelta(kind="content", content="Hello"),
        StreamDelta(
            kind="content",
            content=" world",
            usage=RelayUsage(prompt_tokens=4, completion_tokens=2),
        ),
        StreamDelta(kind="finish", finish_reason="stop"),
    ]


def responses_stream_deltas() -> list[StreamDelta]:
    return [
        StreamDelta(kind="role", role="assistant"),
        StreamDelta(kind="content", content="Hello"),
        StreamDelta(kind="content", content=" world"),
        StreamDelta(
            kind="usage",
            usage=RelayUsage(prompt_tokens=4, completion_tokens=2),
        ),
        StreamDelta(kind="finish", finish_reason="stop"),
        StreamDelta(kind="status", status="completed"),
    ]


STREAM_DELTAS: dict[str, list[StreamDelta]] = {
    "openai": openai_stream_deltas(),
    "claude": claude_stream_deltas(),
    "gemini": gemini_stream_deltas(),
    "openai_responses": responses_stream_deltas(),
}

STREAM_MODEL: dict[str, str] = {
    "openai": "gpt-test",
    "openai_responses": "stream-model",
    "claude": "claude-test",
    "gemini": "upstream-model",
}
STREAM_ID: dict[str, str] = {
    "openai": "chatcmpl-fixed",
    "openai_responses": "stream_fixed",
    "claude": "msg_fixed",
    "gemini": "stream_fixed",
}