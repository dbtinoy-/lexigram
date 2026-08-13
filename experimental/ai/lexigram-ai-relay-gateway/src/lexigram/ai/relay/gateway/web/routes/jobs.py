from __future__ import annotations

"""Job-relay endpoints for submit-then-poll kinds (e.g. video generation)."""

from time import monotonic

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from lexigram.ai.relay.gateway.web.routes.common import (
    ResolveJobPassthrough,
    _log_kind_dispatch,
)
from lexigram.ai.relay.gateway.web.shared import (
    _error_response,
    _parse_body,
    _safe_headers,
)
from lexigram.contracts.ai.relay import (
    RelayFormat,
    RelayGatewayError,
    RelayGatewayRequest,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.identity.ambient import new_uuid


async def job_submit_endpoint(
    kind: str,
    resolve_job_passthrough: ResolveJobPassthrough,
    request: Request,
) -> Response:
    """Serve one job-relay submit request in its own wire format.

    The body is read exactly once and forwarded verbatim: no format
    inference happens, so the request carries the conventional
    ``OPENAI_CHAT`` source marker and no channel hint.  Video is an
    OpenAI-shaped submit/poll convention, so failures render in the
    OpenAI error envelope through the same machinery as the passthrough
    routes.  The job passthrough service is resolved per request, never
    cached.

    Args:
        kind: The endpoint kind owned by this route.
        resolve_job_passthrough: Resolver of the job passthrough
            service.
        request: The Starlette request being served.

    Returns:
        The upstream JSON verbatim (with the id rewritten to the
        gateway-issued job id), ``204`` when the result carries no
        payload, or the OpenAI error envelope for gateway failures.
    """
    started = monotonic()
    raw = await request.body()
    request_id = getattr(request.state, "request_id", None) or new_uuid()
    trace_id = request.headers.get("x-trace-id", "") or ""
    body = _parse_body(raw, RelayFormat.OPENAI_CHAT, request_id)
    if isinstance(body, Response):
        return body
    model_value = body.get("model")
    if not isinstance(model_value, str) or not model_value:
        return _error_response(
            RelayFormat.OPENAI_CHAT,
            RelayGatewayError(
                code=RelayGatewayErrorCode.INVALID_REQUEST,
                message="model is required",
                status_code=400,
                request_id=request_id,
            ),
        )
    user = getattr(request.state, "user", None)
    tenant_id = ""
    if isinstance(user, dict):
        tenant = user.get("tenant_id") or user.get("tenant")
        if isinstance(tenant, str):
            tenant_id = tenant
    gateway_request = RelayGatewayRequest(
        request_id=request_id,
        tenant_id=tenant_id,
        source=RelayFormat.OPENAI_CHAT,
        model=model_value,
        stream=False,
        payload=body,
        headers=dict(request.headers.items()),
        channel=None,
    )
    service = await resolve_job_passthrough(request)
    result = await service.submit(kind, gateway_request)
    if result.is_err():
        error = result.unwrap_err()
        response = _error_response(RelayFormat.OPENAI_CHAT, error)
        await _log_kind_dispatch(
            request, kind, model_value, response.status_code, error.code, started
        )
        return response
    ok_result = result.unwrap()
    headers = _safe_headers(ok_result.headers, request_id, trace_id)
    if ok_result.payload is not None:
        response = JSONResponse(
            content=ok_result.payload,
            status_code=ok_result.status_code,
            headers=headers,
        )
    else:
        response = Response(status_code=204, headers=headers)
    await _log_kind_dispatch(
        request, kind, model_value, response.status_code, "", started
    )
    return response


async def job_status_endpoint(
    kind: str,
    resolve_job_passthrough: ResolveJobPassthrough,
    request: Request,
) -> Response:
    """Serve one job-relay status poll against a gateway-issued job id.

    The job id comes from the path, not the body: status polls carry no
    payload, so the gateway request built here carries an empty payload
    and model, and only identity and request id are meaningful.  The
    status call authorizes but never re-runs the billing pipeline, and
    failures render in the OpenAI error envelope like the other
    sighted routes.

    Args:
        kind: The endpoint kind owned by this route.
        resolve_job_passthrough: Resolver of the job passthrough
            service.
        request: The Starlette request being served.

    Returns:
        The upstream status JSON verbatim (with the id rewritten back to
        the gateway-issued job id), ``204`` when the result carries no
        payload, or the OpenAI error envelope for gateway failures.
    """
    request_id = getattr(request.state, "request_id", None) or new_uuid()
    trace_id = request.headers.get("x-trace-id", "") or ""
    job_id = request.path_params.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        return _error_response(
            RelayFormat.OPENAI_CHAT,
            RelayGatewayError(
                code=RelayGatewayErrorCode.INVALID_REQUEST,
                message="job_id is required",
                status_code=400,
                request_id=request_id,
            ),
        )
    user = getattr(request.state, "user", None)
    tenant_id = ""
    if isinstance(user, dict):
        tenant = user.get("tenant_id") or user.get("tenant")
        if isinstance(tenant, str):
            tenant_id = tenant
    gateway_request = RelayGatewayRequest(
        request_id=request_id,
        tenant_id=tenant_id,
        source=RelayFormat.OPENAI_CHAT,
        model="",
        stream=False,
        payload={},
        headers=dict(request.headers.items()),
        channel=None,
    )
    service = await resolve_job_passthrough(request)
    result = await service.status(kind, job_id, gateway_request)
    if result.is_err():
        return _error_response(RelayFormat.OPENAI_CHAT, result.unwrap_err())
    ok_result = result.unwrap()
    headers = _safe_headers(ok_result.headers, request_id, trace_id)
    if ok_result.payload is not None:
        return JSONResponse(
            content=ok_result.payload,
            status_code=ok_result.status_code,
            headers=headers,
        )
    return Response(status_code=204, headers=headers)
