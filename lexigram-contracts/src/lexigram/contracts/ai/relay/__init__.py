"""Relay conversion shared types — canonical IR and protocol enums.

These types are the contract between the wire DTOs and the converter
engine in ``lexigram-ai-llm``.  Wire DTOs live in ``lexigram.contracts.ai.relay.dto``.
"""

from __future__ import annotations

from lexigram.contracts.ai.relay.ir import (
    RelayError,
    RelayRequest,
    RelayResponse,
    RelayUsage,
)
from lexigram.contracts.ai.relay.types import (
    PassthroughData,
    RelayConfig,
    RelayProtocol,
    StreamMode,
)

__all__ = [
    "PassthroughData",
    "RelayConfig",
    "RelayError",
    "RelayProtocol",
    "RelayRequest",
    "RelayResponse",
    "RelayUsage",
    "StreamMode",
]
