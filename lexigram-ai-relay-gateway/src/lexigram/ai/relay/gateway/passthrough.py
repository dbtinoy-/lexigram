"""Passthrough relay lifecycle for non-chat endpoint kinds.

``PassthroughService`` relays endpoint kinds that do not fit the
chat-focused conversion engine (starting with embeddings) through the
generalized parts of the chat pipeline — channel selection by endpoint
kind, authorization, billing admission and settlement, and the upstream
HTTP adapter — while skipping ``RelayConverterProtocol`` entirely: the
wire format in is the wire format out, with the model alias
substituted only when the channel config declares a suffix.  Bodies are
carried by :class:`RelayPassthroughBody` (decoded JSON or raw bytes
with a content type) and upstream responses by
:class:`RelayPassthroughResult` (verbatim bytes plus the upstream
content type) — JSON responses are still returned decoded through the
``payload`` accessor so the embeddings wire path is byte-for-byte
unchanged, while non-JSON responses ride in ``body`` uninterpreted.
The upstream response is returned verbatim, unvalidated beyond the
adapter's existing malformed-body handling.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Mapping
from dataclasses import dataclass
import time
from typing import Any, Literal, cast

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.errors import (
    auth_denied,
    billing_error_to_gateway,
    with_request_id,
)
from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.contracts.ai.governance import (
    RelayBillingProtocol,
    RelayUsageReservation,
    RelayUsageScope,
)
from lexigram.contracts.ai.relay import (
    ConversionQuality,
    JsonValue,
    RelayChannel,
    RelayConvertResult,
    RelayFormat,
    RelayGatewayError,
    RelayGatewayMetadata,
    RelayGatewayRequest,
    RelayGatewayResult,
    RelayRequestPayload,
    RelayUsage,
    RelayWireEvent,
    UpstreamRequest,
    UpstreamResponse,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.contracts.auth.guard import AuthorizerProtocol
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.logging import get_logger
from lexigram.serialization import dumps

__all__ = [
    "PassthroughService",
    "RelayPassthroughBody",
    "RelayPassthroughResult",
    "rewrite_multipart_form_field",
]

logger = get_logger(__name__)

_JSON_CONTENT_TYPE = "application/json"
_FORM_FIELD_HEADER_MARKER = b'name="'
_FORM_FIELD_HEADER_SUFFIX = b'"'
"""Multipart ``Content-Disposition`` attribute delimiters used by the field rewrite."""

_ENDPOINT_PATHS: dict[str, str] = {
    "embeddings": "/v1/embeddings",
}
"""Endpoint kinds to upstream path segments served by this relay.

Every registered kind uses the OpenAI-shaped ``/v1/<kind>`` path; future
kinds with provider-specific shapes (multipart audio, binary images)
extend this table in their own plans.
"""


@dataclass(frozen=True, slots=True)
class RelayPassthroughBody(Mapping[str, JsonValue]):
    """One forwarded gateway request body: decoded JSON or raw bytes.

    The two constructors are the entire surface: :meth:`json` wraps a
    decoded JSON object (content type ``application/json``) and
    :meth:`raw` wraps arbitrary bytes with their content type, so
    ``multipart/form-data`` requests travel through the same
    ``RelayGatewayRequest.payload`` field as JSON bodies.  The mapping
    facade (``__getitem__``/``__iter__``/``__len__``) delegates to the
    JSON dict for ``json`` bodies and raises ``TypeError`` for raw
    bodies — the passthrough pipeline branches on whether ``data`` is a
    mapping and never treats raw content as JSON.

    Attributes:
        data: The decoded JSON object for ``json`` bodies, or the raw
            body bytes for ``raw`` bodies.
        content_type: Outbound content type header value; ``json``
            bodies always carry ``application/json``.
    """

    data: Mapping[str, JsonValue] | bytes
    content_type: str

    @classmethod
    def json(cls, payload: Mapping[str, JsonValue]) -> RelayPassthroughBody:
        """Wrap a decoded JSON object request body.

        Args:
            payload: The decoded JSON object to forward.

        Returns:
            A JSON body carrying ``application/json`` as its content
            type; the object is shallow-copied so later mutation of the
            source never leaks into the frozen body.
        """
        return cls(dict(payload), _JSON_CONTENT_TYPE)

    @classmethod
    def raw(cls, data: bytes, content_type: str) -> RelayPassthroughBody:
        """Wrap a raw (e.g. ``multipart/form-data``) request body.

        Args:
            data: The raw body bytes to forward verbatim.
            content_type: The body's content type header (boundary
                parameter included for multipart bodies).

        Returns:
            A raw body carrying *content_type* unchanged.
        """
        return cls(data, content_type)

    def __getitem__(self, key: str) -> JsonValue:
        """Return one JSON field for ``json`` bodies.

        Raises:
            TypeError: If the body is raw bytes, which are not JSON.
        """
        data = self.data
        if not isinstance(data, Mapping):
            raise TypeError("raw passthrough bodies are not JSON mappings")
        return data[key]

    def __iter__(self) -> Iterator[str]:
        """Iterate the JSON field names for ``json`` bodies.

        Raises:
            TypeError: If the body is raw bytes, which are not JSON.
        """
        data = self.data
        if not isinstance(data, Mapping):
            raise TypeError("raw passthrough bodies are not JSON mappings")
        return iter(data)

    def __len__(self) -> int:
        """Return the JSON field count for ``json`` bodies.

        Raises:
            TypeError: If the body is raw bytes, which are not JSON.
        """
        data = self.data
        if not isinstance(data, Mapping):
            raise TypeError("raw passthrough bodies are not JSON mappings")
        return len(data)


@dataclass(frozen=True, slots=True, init=False)
class RelayPassthroughResult(RelayGatewayResult):
    """One passthrough upstream response, decoded when JSON, verbatim otherwise.

    Extends the gateway result carrier with the two fields the passthrough
    wire paths need: the upstream body and its content type.  JSON
    responses keep their decoded object on ``payload`` (byte-for-byte the
    Plan J shape) and additionally populate ``body`` with the serialized
    bytes; non-JSON responses carry the raw bytes in ``body`` with
    ``payload`` left ``None``.  Callers read ``body`` regardless of the
    response shape; the constructor is ``(body, content_type,
    status_code)`` with the inherited gateway fields (headers, payload)
    as optional keywords so existing relay route code keeps compiling.

    Attributes:
        body: The response body bytes (serialized JSON for JSON
            responses, the upstream bytes verbatim otherwise).
        content_type: The upstream ``content-type`` header value.
    """

    body: bytes = b""
    content_type: str = ""

    def __init__(
        self,
        body: bytes = b"",
        content_type: str = "",
        status_code: int = 200,
        *,
        headers: Mapping[str, str] | None = None,
        payload: Mapping[str, JsonValue] | None = None,
        stream: AsyncIterator[RelayWireEvent] | None = None,
        metadata: RelayGatewayMetadata | None = None,
    ) -> None:
        """Bind the passthrough result fields.

        Args:
            body: The response body bytes.
            content_type: The upstream content-type header.
            status_code: The upstream HTTP status code.
            headers: Response headers to relay; defaults to empty.
            payload: Decoded JSON object for JSON responses; ``None``
                for raw bodies.
            stream: Never used by passthrough; always ``None``.
            metadata: Never used by passthrough; always ``None``.
        """
        object.__setattr__(self, "body", body)
        object.__setattr__(self, "content_type", content_type)
        object.__setattr__(self, "status_code", status_code)
        object.__setattr__(self, "headers", headers if headers is not None else {})
        object.__setattr__(self, "payload", payload)
        object.__setattr__(self, "stream", stream)
        object.__setattr__(self, "metadata", metadata)


def rewrite_multipart_form_field(
    body: bytes,
    boundary: str,
    field: str,
    value: str,
) -> bytes:
    """Rewrite one named form field's value in a multipart body.

    Narrow boundary-aware rewrite (not a general multipart parser): the
    body is split on the ``--<boundary>`` framing marker and the first
    part whose ``Content-Disposition`` header carries
    ``name="<field>"`` has its value content swapped in place; every
    other byte — headers, other parts, the closing marker — is left
    untouched.  A body without the field (or without the boundary
    marker) is returned unchanged; that is not an error, some
    passthrough endpoints resolve the model from the URL path or a
    channel default instead of a body field.

    Args:
        body: The raw ``multipart/form-data`` body bytes.
        boundary: The boundary token from the content-type header.
        field: The form field name to rewrite (e.g. ``"model"``).
        value: The replacement field value.

    Returns:
        The body with the named field's value replaced, or the body
        unchanged when the field is absent.
    """
    marker = b"--" + boundary.encode("utf-8")
    target = (
        _FORM_FIELD_HEADER_MARKER + field.encode("utf-8") + _FORM_FIELD_HEADER_SUFFIX
    )
    replacement = value.encode("utf-8")
    segments = body.split(marker)
    if len(segments) < 2:
        return body
    for index in range(1, len(segments) - 1):
        part = segments[index]
        separator = part.find(b"\r\n\r\n")
        if separator < 0:
            continue
        headers = part[2:separator].lower()
        if target not in headers:
            continue
        value_end = len(part) - 2 if part.endswith(b"\r\n") else len(part)
        segments[index] = part[: separator + 4] + replacement + part[value_end:]
        return marker.join(segments)
    return body


def _as_relay_body(payload: Mapping[str, JsonValue]) -> RelayPassthroughBody:
    """Normalize a gateway request payload into a relay passthrough body.

    Bodies already carrying the relay carrier pass through unchanged;
    plain JSON mappings (legacy callers) are wrapped as JSON bodies.

    Args:
        payload: The ``RelayGatewayRequest.payload`` value.

    Returns:
        The payload as a :class:`RelayPassthroughBody`.
    """
    if isinstance(payload, RelayPassthroughBody):
        return payload
    return RelayPassthroughBody.json(dict(payload))


def _multipart_boundary(content_type: str) -> str | None:
    """Extract the ``boundary`` parameter from a content-type header.

    Args:
        content_type: The raw content-type header value.

    Returns:
        The boundary token without surrounding quotes, or ``None`` when
        the header carries no boundary parameter.
    """
    for parameter in content_type.split(";"):
        key, separator, raw_value = parameter.strip().partition("=")
        if separator and key.lower() == "boundary":
            return raw_value.strip().strip('"')
    return None


def _is_json_content_type(content_type: str) -> bool:
    """Tell whether a content-type value denotes JSON.

    Args:
        content_type: A content-type header value.

    Returns:
        ``True`` for the exact ``application/json`` media type and for
        any ``*+json`` suffix variant; ``False`` otherwise.
    """
    media_type = content_type.partition(";")[0].strip().lower()
    return media_type == _JSON_CONTENT_TYPE or media_type.endswith("+json")


@dataclass(frozen=True, slots=True)
class _PassthroughPayloadCarrier:
    """Billing-admission carrier for a passthrough request body.

    Passthrough bodies do not belong to any chat wire DTO, so the
    shared billing pipeline receives a transparent carrier: prompt
    estimation counts the serialized body (same estimate function as the
    chat path) and the requested output budget is unknown, so zero is
    reserved. The carrier quacks like a ``RelayRequestPayload`` at the
    only call site the billing pipeline uses (``to_dict``).
    """

    body: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return the passthrough body.

        Returns:
            A shallow copy of the forwarded request body.
        """
        return dict(self.body)


class PassthroughService:
    """Endpoint-kind mapping: call one method, no conversion.

    The service is stateless between requests and never includes
    payloads or upstream details in error messages; errors are always
    safe ``RelayGatewayError`` values.  Authorization, billing, channel
    selection, and upstream transport reuse the chat pipeline's
    dependencies unchanged.

    Attributes:
        _registry: Deterministic channel selector.
        _upstream: HTTP transport adapter.
        _config: Gateway configuration (channel table and model suffixes).
        _authorizer: Optional authorization check before dispatch.
        _billing: Optional billing lifecycle; when ``None`` admission and
            settlement are skipped.
    """

    def __init__(
        self,
        registry: RelayChannelRegistry,
        upstream: HTTPUpstreamAdapter,
        config: RelayGatewayConfig,
        *,
        authorizer: AuthorizerProtocol | None = None,
        billing: RelayBillingProtocol | None = None,
    ) -> None:
        """Bind the service to its dependencies.

        Args:
            registry: Channel selection registry.
            upstream: Upstream transport adapter; handles credential
                injection per channel through its configured provider.
            config: Static gateway configuration.
            authorizer: Optional authorizer; when ``None`` authorization
                is skipped.
            billing: Optional billing lifecycle; when ``None`` the
                passthrough runs without admission control or settlement.
        """
        self._registry = registry
        self._upstream = upstream
        self._config = config
        self._authorizer = authorizer
        self._billing = billing

    async def handle(
        self, kind: str, request: RelayGatewayRequest
    ) -> Result[RelayPassthroughResult, RelayGatewayError]:
        """Run the passthrough lifecycle for one request.

        Dependencies run in fixed order: authorize, select channel by
        endpoint kind, reserve billing capacity, call upstream with the
        caller's body verbatim, settle billing, assemble result.  Any
        failure short-circuits the pipeline.

        Args:
            kind: The endpoint kind being served (e.g. ``"embeddings"``).
            request: The passthrough gateway request; ``payload`` is
                either a ``RelayPassthroughBody`` (JSON or raw multipart)
                or a plain JSON mapping forwarded by legacy callers, and
                ``source`` is a conventional marker (``OPENAI_CHAT``)
                never used for conversion.

        Returns:
            ``Ok(RelayPassthroughResult)`` on success, or
            ``Err(RelayGatewayError)`` on the first failure.  Unexpected
            exceptions from dependencies never escape: they are logged
            and mapped to a generic ``CONVERSION_FAILED`` error.
        """
        started = time.monotonic()
        logger.info(
            "relay_passthrough_request_accepted",
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            endpoint=kind,
            model=request.model,
        )
        try:
            result, channel_name = await self._dispatch(kind, request)
        except Exception as exc:
            logger.warning(
                "relay_passthrough_unexpected_error",
                request_id=request.request_id,
                endpoint=kind,
                error=str(exc),
            )
            error = self._unexpected_error(request.request_id)
            self._log_request_completed(request, kind, "", error, started)
            return Err(error)
        if result.is_err():
            self._log_request_completed(
                request, kind, channel_name, result.unwrap_err(), started
            )
            return result
        outcome = result.unwrap()
        self._log_request_completed(request, kind, channel_name, outcome, started)
        return result

    async def _dispatch(
        self,
        kind: str,
        request: RelayGatewayRequest,
    ) -> tuple[Result[RelayPassthroughResult, RelayGatewayError], str]:
        """Run the ordered dependency pipeline for one request.

        Returns:
            ``tuple`` of the pipeline result and the selected channel
            name.  The channel name is ``""`` when selection failed
            before a channel was chosen.
        """
        if kind not in _ENDPOINT_PATHS:
            return (
                Err(
                    RelayGatewayError(
                        code=RelayGatewayErrorCode.INVALID_REQUEST,
                        message="unsupported endpoint kind",
                        status_code=400,
                        request_id=request.request_id,
                        retryable=False,
                    )
                ),
                "",
            )
        if self._authorizer is not None:
            allowed = await self._authorizer.authorize(
                user=request.tenant_id,
                action="relay.invoke",
                resource=request.model,
            )
            if not allowed:
                return Err(auth_denied(request.request_id)), ""
        selected = self._registry.select_for_endpoint(
            kind=kind,
            model=request.model,
        )
        if selected.is_err():
            return (
                Err(with_request_id(selected.unwrap_err(), request.request_id)),
                "",
            )
        channel = selected.unwrap()
        logger.info(
            "relay_passthrough_channel_selected",
            request_id=request.request_id,
            endpoint=kind,
            channel=channel.name,
            model=request.model,
        )
        billing = self._billing
        reservation: RelayUsageReservation | None = None
        if billing is not None:
            admitted = await self._reserve(request, billing, channel)
            if admitted.is_err():
                return Err(admitted.unwrap_err()), channel.name
            reservation = admitted.unwrap()
        body = _as_relay_body(request.payload)
        outbound_model = request.model + self._config.model_suffix.get(channel.name, "")
        body_data = body.data
        if isinstance(body_data, Mapping):
            outbound = dict(body_data)
            outbound["model"] = outbound_model
            upstream_response = await self._call_upstream(
                kind, channel, outbound, body.content_type, request
            )
        else:
            content_type = body.content_type
            boundary = _multipart_boundary(content_type)
            outbound_raw = body_data
            if boundary is not None:
                outbound_raw = rewrite_multipart_form_field(
                    outbound_raw, boundary, "model", outbound_model
                )
            upstream_response = await self._call_upstream(
                kind, channel, outbound_raw, content_type, request
            )
        if upstream_response.is_err():
            if billing is not None and reservation is not None:
                await self._settle_failed(billing, reservation)
            return (
                Err(
                    with_request_id(upstream_response.unwrap_err(), request.request_id)
                ),
                channel.name,
            )
        resp = upstream_response.unwrap()
        payload = resp.payload
        if isinstance(payload, Mapping) and _is_json_content_type(
            resp.headers.get("content-type", _JSON_CONTENT_TYPE)
        ):
            if billing is not None and reservation is not None:
                await self._settle(
                    billing,
                    reservation,
                    self._usage_from_response(payload),
                    status="completed",
                )
            return (
                Ok(
                    RelayPassthroughResult(
                        status_code=resp.status_code,
                        headers={**resp.headers, "x-request-id": request.request_id},
                        payload=payload,
                        stream=None,
                        metadata=None,
                        body=dumps(payload),
                        content_type=resp.headers.get(
                            "content-type", _JSON_CONTENT_TYPE
                        ),
                    )
                ),
                channel.name,
            )
        if isinstance(payload, bytes):
            if billing is not None and reservation is not None:
                await self._settle(billing, reservation, None, status="completed")
            return (
                Ok(
                    RelayPassthroughResult(
                        status_code=resp.status_code,
                        headers={**resp.headers, "x-request-id": request.request_id},
                        payload=None,
                        stream=None,
                        metadata=None,
                        body=payload,
                        content_type=resp.headers.get("content-type", ""),
                    )
                ),
                channel.name,
            )
        if billing is not None and reservation is not None:
            await self._settle_failed(billing, reservation)
        return (
            Err(
                RelayGatewayError(
                    code=RelayGatewayErrorCode.UPSTREAM_MALFORMED,
                    message="malformed upstream response",
                    status_code=502,
                    request_id=request.request_id,
                    retryable=False,
                )
            ),
            channel.name,
        )

    async def _reserve(
        self,
        request: RelayGatewayRequest,
        billing: RelayBillingProtocol,
        channel: RelayChannel,
    ) -> Result[RelayUsageReservation, RelayGatewayError]:
        """Reserve billing capacity before the upstream call.

        The passthrough body is wrapped in a transparent carrier so the
        shared billing pipeline can estimate prompt tokens from the
        serialized body; the output budget is unknown and reserved as
        zero.  Billing denials short-circuit the pipeline and are
        classified through :func:`billing_error_to_gateway`.

        Args:
            request: The passthrough request being dispatched.
            billing: The billing lifecycle to reserve through.
            channel: The selected channel.

        Returns:
            ``Ok(reservation)`` when admission is proven, or
            ``Err(RelayGatewayError)`` carrying the classified failure.
        """
        scope = RelayUsageScope(
            tenant_id=request.tenant_id,
            model=request.model,
            channel=channel.name,
        )
        body = _as_relay_body(request.payload)
        body_data = body.data
        if isinstance(body_data, Mapping):
            carrier_body: dict[str, JsonValue] = dict(body_data)
        else:
            carrier_body = {}
        carrier = _PassthroughPayloadCarrier(carrier_body)
        admitted = await billing.pre_consume(
            request.request_id,
            scope,
            cast("RelayRequestPayload", carrier),
        )
        if admitted.is_err():
            error = admitted.unwrap_err()
            logger.warning(
                "relay_passthrough_billing_denied",
                request_id=request.request_id,
                channel=channel.name,
                code=error.code,
                error=error.message,
            )
            return Err(billing_error_to_gateway(error, request.request_id))
        return Ok(admitted.unwrap())

    async def _settle(
        self,
        billing: RelayBillingProtocol,
        reservation: RelayUsageReservation,
        usage: RelayUsage | None,
        *,
        status: Literal["completed", "failed", "cancelled", "truncated"],
    ) -> None:
        """Settle the reservation exactly once without failing the response.

        Settlement failures are logged and never propagate: the response
        path has already completed by the time accounting runs.

        Args:
            billing: The billing lifecycle to settle through.
            reservation: The reservation granted by ``pre_consume``.
            usage: The usage extracted from the upstream response, or
                ``None`` when the response omits it.
            status: Terminal lifecycle status of the attempt.
        """
        result = RelayConvertResult[Any](
            value=None,
            source=RelayFormat.OPENAI_CHAT,
            target=RelayFormat.OPENAI_CHAT,
            converter_id="passthrough",
            quality=ConversionQuality.GOOD,
            usage=usage,
        )
        settled = await billing.settle(reservation, result, status=status)
        if settled.is_err():
            error = settled.unwrap_err()
            logger.warning(
                "relay_passthrough_settle_failed",
                request_id=reservation.request_id,
                status=status,
                code=error.code,
                error=error.message,
            )

    async def _settle_failed(
        self,
        billing: RelayBillingProtocol,
        reservation: RelayUsageReservation,
    ) -> None:
        """Settle a failed attempt without usage through the billing pipeline.

        Args:
            billing: The billing lifecycle to settle through.
            reservation: The reservation granted by ``pre_consume``.
        """
        await self._settle(billing, reservation, None, status="failed")

    async def _call_upstream(
        self,
        kind: str,
        channel: RelayChannel,
        payload: Mapping[str, JsonValue] | bytes,
        content_type: str,
        request: RelayGatewayRequest,
    ) -> Result[UpstreamResponse, RelayGatewayError]:
        """Send the passthrough body to the selected channel's endpoint.

        Uses the same ``HTTPUpstreamAdapter`` as the chat path, so
        channel-credential injection applies unchanged.  JSON bodies go
        out as their decoded dict; raw bodies (multipart) travel through
        the adapter's payload slot as opaque bytes with their content
        type header intact, so the binary parts reach the provider
        untouched.

        Args:
            kind: The endpoint kind being served, selecting the wire path.
            channel: The selected channel.
            payload: The caller's body with the model substituted; a
                decoded JSON object or raw body bytes.
            content_type: The outbound content type header value.
            request: The original gateway request.

        Returns:
            ``Ok(UpstreamResponse)`` or ``Err`` as returned by the
            adapter; the adapter already normalizes transport failures.
        """
        url = self._endpoint_url(kind, channel)
        logger.info(
            "relay_passthrough_upstream_started",
            request_id=request.request_id,
            channel=channel.name,
            method="POST",
            url=url,
        )
        upstream = await self._upstream.request(
            UpstreamRequest(
                request_id=request.request_id,
                method="POST",
                url=url,
                headers={"content-type": content_type},
                payload=cast("Mapping[str, JsonValue]", payload),
                timeout_seconds=channel.timeout_seconds,
                channel_name=channel.name,
            )
        )
        if upstream.is_err():
            err = upstream.unwrap_err()
            logger.warning(
                "relay_passthrough_upstream_failed",
                request_id=request.request_id,
                channel=channel.name,
                code=err.code,
                status_code=err.status_code,
                error=str(err),
            )
        return upstream

    def _endpoint_url(self, kind: str, channel: RelayChannel) -> str:
        """Build the endpoint URL for *kind* on *channel*.

        Args:
            kind: The endpoint kind being served.
            channel: The selected channel.

        Returns:
            ``<channel base>/v1/<kind>`` for a registered kind; the
            kind was validated against ``_ENDPOINT_PATHS`` before the
            channel call, so this never misses.
        """
        base = channel.upstream_base_url.rstrip("/")
        return f"{base}{_ENDPOINT_PATHS[kind]}"

    @staticmethod
    def _usage_from_response(payload: Mapping[str, Any]) -> RelayUsage | None:
        """Extract normalized usage from an OpenAI-shaped response body.

        Args:
            payload: The upstream response body.

        Returns:
            ``RelayUsage`` when the body carries an integer
            ``prompt_tokens`` count, otherwise ``None`` (the billing
            pipeline records usage as missing).
        """
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            return None
        prompt = usage.get("prompt_tokens")
        if not isinstance(prompt, int):
            return None
        completion = usage.get("completion_tokens", 0)
        if not isinstance(completion, int):
            completion = 0
        return RelayUsage(prompt_tokens=prompt, completion_tokens=completion)

    @staticmethod
    def _unexpected_error(request_id: str) -> RelayGatewayError:
        """Build the generic error for unexpected dependency failures."""
        return RelayGatewayError(
            code=RelayGatewayErrorCode.CONVERSION_FAILED,
            message="Unexpected relay gateway failure",
            status_code=500,
            request_id=request_id,
            retryable=False,
        )

    def _log_request_completed(
        self,
        request: RelayGatewayRequest,
        kind: str,
        channel_name: str,
        outcome: RelayGatewayResult | RelayGatewayError,
        started: float,
    ) -> None:
        """Emit the terminal request-completed event for any outcome.

        Args:
            request: The original gateway request.
            kind: The endpoint kind that was served.
            channel_name: Selected channel name (or ``""`` when unknown).
            outcome: The success result or the error that ended the flow.
            started: Monotonic start time used to compute the duration.
        """
        logger.info(
            "relay_passthrough_request_completed",
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            endpoint=kind,
            channel=channel_name,
            status_code=outcome.status_code,
            code=outcome.code if isinstance(outcome, RelayGatewayError) else "OK",
            duration_ms=round((time.monotonic() - started) * 1000, 2),
        )
