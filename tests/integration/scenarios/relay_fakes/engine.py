"""Fake relay converter and stream session for scenario tests."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from lexigram.contracts.ai.relay import (
    ConversionQuality,
    RelayConverterProtocol,
    RelayConvertResult,
    RelayFormat,
    RelayRequestPayload,
    RelayResponsePayload,
    RelayUsage,
)
from lexigram.contracts.ai.relay.operations import (
    RelayActiveStream,
    RelayChannelHealth,
    RelayOperationsControlProtocol,
    RelayOperationsProtocol,
    RelayPolicyChange,
    RelayPolicySnapshot,
    RelayRegistryDiagnostics,
    RelayRouteMetrics,
    TimeWindow,
)
from lexigram.contracts.ai.relay.protocols import (
    RelayRegistryProtocol,
    RelayStreamSessionProtocol,
)
from lexigram.contracts.core.result import Err, Ok, Result


@dataclass
class FakeRelayConverter(RelayConverterProtocol):
    """Converter that echoes payloads and records conversion directions.

    Attributes:
        conversions: ``(kind, source, target)`` tuples per request.
        request_result: Scripted request conversion result.
        response_result: Scripted response conversion result.
        session: Scripted stream session returned by ``new_stream_session``.
    """

    conversions: list[tuple[str, RelayFormat, RelayFormat]] = field(
        default_factory=list
    )
    request_result: RelayConvertResult[RelayRequestPayload] | None = None
    response_result: RelayConvertResult[RelayResponsePayload] | None = None
    session: RelayStreamSessionProtocol | None = None

    def convert_request(
        self,
        payload: RelayRequestPayload,
        source: RelayFormat,
        target: RelayFormat,
        *,
        context: object | None = None,
        registry: RelayRegistryProtocol | None = None,
    ) -> Result[RelayConvertResult[RelayRequestPayload], object]:
        del context, registry
        self.conversions.append(("request", source, target))
        if self.request_result is not None:
            return Ok(self.request_result)
        # The gateway serializes the converted value with ``to_dict()``,
        # so the fake produces the typed target DTO through the real codec.
        from lexigram.ai.relay.gateway.codec import RelayPayloadCodec
        from lexigram.serialization import dumps

        decoded = RelayPayloadCodec().decode_request(
            target, dumps(payload), request_id=""
        )
        if decoded.is_err():
            return Err(decoded.unwrap_err())
        return Ok(
            RelayConvertResult(
                value=decoded.unwrap(),
                source=source,
                target=target,
                converter_id=f"{source.value}_to_{target.value}",
                quality=ConversionQuality.GOOD,
            )
        )

    def convert_response(
        self,
        payload: RelayResponsePayload,
        source: RelayFormat,
        target: RelayFormat,
        *,
        context: object | None = None,
        registry: RelayRegistryProtocol | None = None,
    ) -> Result[RelayConvertResult[RelayResponsePayload], object]:
        del context, registry
        self.conversions.append(("response", source, target))
        if self.response_result is not None:
            return Ok(self.response_result)
        return Ok(
            RelayConvertResult(
                value=payload,
                source=source,
                target=target,
                converter_id=f"{source.value}_to_{target.value}",
                quality=ConversionQuality.GOOD,
                usage=RelayUsage(prompt_tokens=5, completion_tokens=3),
            )
        )

    def new_stream_session(
        self,
        source: RelayFormat,
        target: RelayFormat,
        *,
        options: Mapping[str, object] | None = None,
        context: object | None = None,
        registry: RelayRegistryProtocol | None = None,
    ) -> Result[RelayStreamSessionProtocol, object]:
        del options, context, registry
        if self.session is not None:
            return Ok(self.session)
        return Err(PermissionError("no fake stream session configured"))

    def convert_stream_chunk(
        self,
        session: RelayStreamSessionProtocol,
        event: object,
    ) -> tuple[object, ...]:
        return session.accept(event)

    def finalize(
        self,
        session: RelayStreamSessionProtocol,
    ) -> tuple[object, ...]:
        return session.finalize()


class FakeStreamSession(RelayStreamSessionProtocol):
    """A scripted stream session whose source events are accepted verbatim.

    Attributes:
        accepted: Events passed through ``accept`` (already normalized).
        finalized: A stable marker returned one time by ``finalize``.
        snapshots: list of snapshot values returned by ``snapshot``.
    """

    def __init__(self) -> None:
        """Bind an empty script with no finalized marker."""
        self.accepted: list[object] = []
        self._finalized = False
        self.snapshots: list[object] = []

    def accept(self, event: object) -> tuple[object, ...]:
        """Record and pass one event through unchanged."""
        self.accepted.append(event)
        return (event,)

    def finalize(self) -> tuple[object, ...]:
        """Return a terminal marker exactly once."""
        if self._finalized:
            return ()
        self._finalized = True
        return ({"terminal": True},)

    def snapshot(self) -> object:
        """Record and return the current session snapshot."""
        snapshot = {"accepted": len(self.accepted), "finalized": self._finalized}
        self.snapshots.append(snapshot)
        return snapshot
