"""Typed per-format mapper interfaces for the relay conversion engine.

Each wire format implements one :class:`FormatMapper` with the six
canonical operations: request/response in both directions plus
stream conversion in both directions.  Mappers may reject a feature by
recording a :class:`RelayLoss` and a warning, but must return
``Err(RelayError)`` for malformed or impossible payloads.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

from lexigram.ai.relay.context import ConversionContext
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay.ir import (
    RelayRequest,
    RelayResponse,
    StreamDelta,
    StreamState,
)
from lexigram.contracts.ai.relay.types import RelayFormat, RelayLoss
from lexigram.contracts.core.result import Result

__all__ = ["FormatMapper", "record_loss", "warning_messages"]


@runtime_checkable
class FormatMapper(Protocol):
    """One wire format's typed bidirectional mapping to the canonical IR.

    Concrete mappers implement the same operations the container-facing
    ``RelayMapperProtocol`` declares; the registry in the relay engine
    holds :class:`FormatMapper` implementations.
    """

    def request_to_ir(
        self, payload: Any, *, context: ConversionContext
    ) -> Result[RelayRequest, RelayError]:
        """Convert a source request DTO into canonical ``RelayRequest``."""
        ...

    def ir_to_request(
        self, request: RelayRequest, *, context: ConversionContext
    ) -> Result[Any, RelayError]:
        """Convert a canonical ``RelayRequest`` into the target request DTO."""
        ...

    def response_to_ir(
        self, payload: Any, *, context: ConversionContext
    ) -> Result[RelayResponse, RelayError]:
        """Convert a source response DTO into canonical ``RelayResponse``."""
        ...

    def ir_to_response(
        self, response: RelayResponse, *, context: ConversionContext
    ) -> Result[Any, RelayError]:
        """Convert a canonical ``RelayResponse`` into the target response DTO."""
        ...

    def stream_to_delta(
        self, event: Any, *, state: StreamState
    ) -> Result[tuple[StreamDelta, ...], RelayError]:
        """Convert one source stream event into canonical ``StreamDelta``s."""
        ...

    def delta_to_stream(
        self, delta: StreamDelta, *, state: StreamState
    ) -> Result[tuple[Any, ...], RelayError]:
        """Convert one canonical ``StreamDelta`` into target stream events."""
        ...


def record_loss(
    context: ConversionContext,
    *,
    field: str,
    target: RelayFormat,
    reason: str,
    severity: str = "warning",
) -> None:
    """Record a semantic loss on the conversion context.

    The engine copies the accumulated losses into the
    ``RelayConvertResult`` and surfaces ``warning``/``error`` losses as
    warnings.

    Args:
        context: The per-conversion context holding the loss sink.
        field: Source wire field (or feature) that was dropped or adapted.
        target: Target format the loss applies to.
        reason: Machine-readable reason (e.g. ``json_mode_not_supported``).
        severity: ``error``, ``warning``, or ``info``.
    """
    context.losses.append(
        RelayLoss(field=field, target=target, reason=reason, severity=severity)
    )


def warning_messages(losses: Sequence[RelayLoss]) -> tuple[str, ...]:
    """Render losses into stable warning strings.

    Args:
        losses: Loss records accumulated during conversion.

    Returns:
        One ``"field: reason (target, severity)"`` string per loss.
    """
    return tuple(
        f"{loss.field}: {loss.reason} ({loss.target.value}, {loss.severity})"
        for loss in losses
    )
