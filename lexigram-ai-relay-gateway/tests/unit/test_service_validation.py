"""Relay gateway input validation boundary tests.

Verifies that malformed ``RelayGatewayRequest`` payloads are rejected at
the ``handle`` entry point with ``Err(RelayGatewayError)``
(``INVALID_REQUEST``, 400) instead of raising or flowing downstream.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay.gateway.service import (
    validate_gateway_request,
)
from lexigram.contracts.ai.relay import RelayGatewayError
from tests.unit.service_test_helpers import (
    REQUEST_ID,
    happy_service,
    make_request,
)


class TestValidateGatewayRequest:
    """The pure boundary validator rejects malformed request fields."""

    def test_valid_request_accepts(self) -> None:
        assert validate_gateway_request(make_request()) is None

    def test_empty_request_id_rejected(self) -> None:
        error = validate_gateway_request(make_request(request_id=""))
        assert isinstance(error, RelayGatewayError)
        assert error.code == "INVALID_REQUEST"
        assert error.status_code == 400
        assert error.message == "request_id is required"

    def test_empty_model_rejected(self) -> None:
        error = validate_gateway_request(make_request(model=""))
        assert isinstance(error, RelayGatewayError)
        assert error.code == "INVALID_REQUEST"
        assert error.message == "model is required"

    def test_empty_payload_rejected(self) -> None:
        request = make_request()
        request = request.__class__(
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            source=request.source,
            model=request.model,
            stream=request.stream,
            payload={},
            headers=request.headers,
            channel=request.channel,
        )
        error = validate_gateway_request(request)
        assert isinstance(error, RelayGatewayError)
        assert error.code == "INVALID_REQUEST"
        assert error.message == "payload must be a non-empty object"

    def test_messages_not_a_list_rejected(self) -> None:
        request = make_request()
        request = request.__class__(
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            source=request.source,
            model=request.model,
            stream=request.stream,
            payload={"messages": "hi"},
            headers=request.headers,
            channel=request.channel,
        )
        error = validate_gateway_request(request)
        assert isinstance(error, RelayGatewayError)
        assert error.code == "INVALID_REQUEST"
        assert error.message == "payload messages must be a list"

    def test_empty_messages_list_accepted(self) -> None:
        assert validate_gateway_request(make_request()) is None

    def test_non_object_message_entry_rejected(self) -> None:
        request = make_request()
        request = request.__class__(
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            source=request.source,
            model=request.model,
            stream=request.stream,
            payload={"messages": ["not-an-object"]},
            headers=request.headers,
            channel=request.channel,
        )
        error = validate_gateway_request(request)
        assert isinstance(error, RelayGatewayError)
        assert error.code == "INVALID_REQUEST"
        assert error.message == "payload messages entries must be objects"

    def test_non_mapping_headers_rejected(self) -> None:
        request = make_request()
        request = request.__class__(
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            source=request.source,
            model=request.model,
            stream=request.stream,
            payload=request.payload,
            headers=None,  # type: ignore[arg-type]
            channel=request.channel,
        )
        error = validate_gateway_request(request)
        assert isinstance(error, RelayGatewayError)
        assert error.code == "INVALID_REQUEST"
        assert error.message == "headers must be an object"


class TestHandleValidation:
    """``handle`` returns ``Err(RelayGatewayError)`` for malformed requests."""

    @pytest.mark.asyncio
    async def test_empty_model_returns_err_not_raise(self) -> None:
        service = happy_service([])
        result = await service.handle(make_request(model=""))
        assert result.is_err()
        error = result.unwrap_err()
        assert error.code == "INVALID_REQUEST"
        assert error.status_code == 400
        assert error.request_id == REQUEST_ID

    @pytest.mark.asyncio
    async def test_empty_request_id_returns_err(self) -> None:
        service = happy_service([])
        result = await service.handle(make_request(request_id=""))
        assert result.is_err()
        assert result.unwrap_err().code == "INVALID_REQUEST"

    @pytest.mark.asyncio
    async def test_empty_payload_returns_err(self) -> None:
        service = happy_service([])
        request = make_request()
        request = request.__class__(
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            source=request.source,
            model=request.model,
            stream=request.stream,
            payload={},
            headers=request.headers,
            channel=request.channel,
        )
        result = await service.handle(request)
        assert result.is_err()
        assert result.unwrap_err().code == "INVALID_REQUEST"

    @pytest.mark.asyncio
    async def test_malformed_messages_returns_err(self) -> None:
        service = happy_service([])
        request = make_request()
        request = request.__class__(
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            source=request.source,
            model=request.model,
            stream=request.stream,
            payload={"messages": "nope"},
            headers=request.headers,
            channel=request.channel,
        )
        result = await service.handle(request)
        assert result.is_err()
        assert result.unwrap_err().code == "INVALID_REQUEST"

    @pytest.mark.asyncio
    async def test_empty_messages_list_is_valid(self) -> None:
        service = happy_service([])
        result = await service.handle(make_request())
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_rejected_request_never_reaches_dependencies(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = happy_service(calls)
        result = await service.handle(make_request(model=""))
        assert result.is_err()
        assert calls == []

    @pytest.mark.asyncio
    async def test_streaming_request_with_empty_model_returns_err(self) -> None:
        service = happy_service([])
        result = await service.handle(make_request(model="", stream=True))
        assert result.is_err()
        assert result.unwrap_err().code == "INVALID_REQUEST"
