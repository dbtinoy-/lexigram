"""Passthrough relay service: non-chat endpoint kinds, no conversion.

:class:`PassthroughService` relays endpoint kinds that do not fit the
chat-focused conversion engine (starting with embeddings) through the
generalized parts of the chat pipeline — channel selection by endpoint
kind, authorization, billing admission and settlement, and the upstream
HTTP adapter — while skipping ``RelayConverterProtocol`` entirely: the
wire format in is the wire format out, with the model alias
substituted only when the channel config declares a suffix.

Billing admission/settlement lives in
:mod:`lexigram.ai.relay.gateway._passthrough_billing`; upstream transport
lives in :mod:`lexigram.ai.relay.gateway._passthrough_transport`.
"""

from __future__ import annotations

from collections.abc import Mapping
import time
from typing import TYPE_CHECKING

from lexigram.ai.relay.gateway._passthrough_billing import (
    PassthroughBilling,
    usage_from_response,
)
from lexigram.ai.relay.gateway._passthrough_transport import (
    ENDPOINT_PATHS,
    call_upstream,
)
from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.errors import (
    auth_denied,
    with_request_id,
)
from lexigram.ai.relay.gateway.passthrough_body import (
    _JSON_CONTENT_TYPE,
    _as_relay_body,
    _is_json_content_type,
    _multipart_boundary,
    rewrite_multipart_form_field,
)
from lexigram.ai.relay.gateway.passthrough_result import RelayPassthroughResult
from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.contracts.ai.governance import (
    RelayBillingProtocol,
    RelayUsageReservation,
)
from lexigram.contracts.ai.relay import (
    RelayGatewayError,
    RelayGatewayRequest,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.contracts.auth.guard import AuthorizerProtocol
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.logging import get_logger
from lexigram.serialization import dumps

if TYPE_CHECKING:
    from lexigram.contracts.ai.relay import RelayGatewayResult

__all__ = ["PassthroughService"]

logger = get_logger(__name__)


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
        _billing: Optional billing collaborator; when ``None`` admission
            and settlement are skipped.
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
        self._billing = PassthroughBilling(billing) if billing is not None else None

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
        if kind not in ENDPOINT_PATHS:
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
            admitted = await billing.reserve(request, channel)
            if admitted.is_err():
                return Err(admitted.unwrap_err()), channel.name
            reservation = admitted.unwrap()
        body = _as_relay_body(request.payload)
        outbound_model = channel.resolve_model(
            request.model
        ) + self._config.model_suffix.get(channel.name, "")
        body_data = body.data
        if isinstance(body_data, Mapping):
            outbound = dict(body_data)
            outbound["model"] = outbound_model
            upstream_response = await call_upstream(
                self._upstream,
                kind,
                channel,
                outbound,
                body.content_type,
                request,
            )
        else:
            content_type = body.content_type
            boundary = _multipart_boundary(content_type)
            outbound_raw = body_data
            if boundary is not None:
                outbound_raw = rewrite_multipart_form_field(
                    outbound_raw, boundary, "model", outbound_model
                )
            upstream_response = await call_upstream(
                self._upstream,
                kind,
                channel,
                outbound_raw,
                content_type,
                request,
            )
        if upstream_response.is_err():
            if billing is not None and reservation is not None:
                await billing.settle_failed(reservation)
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
                await billing.settle_completed(
                    reservation, usage_from_response(payload)
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
                await billing.settle_completed(reservation, None)
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
            await billing.settle_failed(reservation)
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
