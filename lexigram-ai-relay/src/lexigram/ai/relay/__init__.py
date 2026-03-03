"""Relay protocol conversion engine for the Lexigram AI subsystem.

This package implements the pure, synchronous conversion engine that
shapes OpenAI Chat Completions, OpenAI Responses, Anthropic Messages,
and Gemini generateContent wire payloads into one canonical IR.  It
performs no HTTP, channel selection, billing, or model selection.
"""

from __future__ import annotations

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.engine import (
    RelayConverterEngine,
    convert_request_by_id,
    convert_request_via,
    convert_response_by_id,
    convert_response_via,
)
from lexigram.ai.relay.errors import (
    malformed_payload,
    media_resolution_required,
    missing_required_option,
    translate,
    unsupported_feature,
    unsupported_format,
)
from lexigram.ai.relay.mappers.base import FormatMapper, record_loss, warning_messages
from lexigram.ai.relay.module import RelayModule
from lexigram.ai.relay.quality import ROUTE_QUALITY, route_quality
from lexigram.ai.relay.registry import RelayConverterRegistry, RouteSpec

__all__ = [
    "ROUTE_QUALITY",
    "ConversionContext",
    "FormatMapper",
    "RelayConverterEngine",
    "RelayConverterRegistry",
    "RelayModule",
    "RouteSpec",
    "convert_request_by_id",
    "convert_request_via",
    "convert_response_by_id",
    "convert_response_via",
    "malformed_payload",
    "media_resolution_required",
    "missing_required_option",
    "record_loss",
    "route_quality",
    "translate",
    "unsupported_feature",
    "unsupported_format",
    "warning_messages",
]
