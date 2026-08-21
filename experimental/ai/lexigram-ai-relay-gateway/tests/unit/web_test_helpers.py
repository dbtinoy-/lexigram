"""Shared test doubles for the relay gateway web-layer tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from lexigram.contracts.ai.relay import (
    RelayGatewayError,
    RelayGatewayProtocol,
    RelayGatewayRequest,
    RelayGatewayResult,
)
from lexigram.contracts.core.result import Ok, Result


class FakeGateway(RelayGatewayProtocol):
    """Minimal ``RelayGatewayProtocol`` double recording ``handle`` calls."""

    def __init__(self, outcome: Result[RelayGatewayResult, RelayGatewayError]) -> None:
        self._outcome = outcome
        self.calls: list[RelayGatewayRequest] = []

    async def handle(
        self, request: RelayGatewayRequest
    ) -> Result[RelayGatewayResult, RelayGatewayError]:
        """Record the request and return the canned outcome."""
        self.calls.append(request)
        return self._outcome

class FakeResolver:
    """Async callable returning the configured fake gateway."""

    def __init__(self, gateway: FakeGateway) -> None:
        self._gateway = gateway
        self.calls: list[Any] = []

    async def __call__(self, request: Any) -> RelayGatewayProtocol:
        """Record the request and return the fake gateway."""
        self.calls.append(request)
        return self._gateway

class FakePassthroughService:
    """Minimal ``PassthroughService`` double recording ``handle`` calls."""

    def __init__(
        self,
        outcome: Result[RelayGatewayResult, RelayGatewayError],
    ) -> None:
        self._outcome = outcome
        self.calls: list[tuple[str, RelayGatewayRequest]] = []

    async def handle(
        self, kind: str, request: RelayGatewayRequest
    ) -> Result[RelayGatewayResult, RelayGatewayError]:
        """Record the call and return the canned outcome."""
        self.calls.append((kind, request))
        return self._outcome

class FakePassthroughResolver:
    """Async callable returning the configured fake passthrough service."""

    def __init__(self, service: FakePassthroughService) -> None:
        self._service = service
        self.calls: list[Any] = []

    async def __call__(self, request: Any) -> FakePassthroughService:
        """Record the request and return the fake service."""
        self.calls.append(request)
        return self._service

class FakeJobPassthroughService:
    """Minimal ``JobPassthroughService`` double recording submit/status calls."""

    def __init__(
        self,
        submit_outcome: Result[RelayGatewayResult, RelayGatewayError] | None = None,
        status_outcome: Result[RelayGatewayResult, RelayGatewayError] | None = None,
    ) -> None:
        self._submit_outcome = submit_outcome
        self._status_outcome = status_outcome
        self.submit_calls: list[tuple[str, RelayGatewayRequest]] = []
        self.status_calls: list[tuple[str, str, RelayGatewayRequest]] = []

    async def submit(
        self, kind: str, request: RelayGatewayRequest
    ) -> Result[RelayGatewayResult, RelayGatewayError]:
        """Record the call and return the canned submit outcome."""
        self.submit_calls.append((kind, request))
        if self._submit_outcome is None:
            return Ok(RelayGatewayResult(status_code=200, headers={}, payload={}))
        return self._submit_outcome

    async def status(
        self, kind: str, gateway_job_id: str, request: RelayGatewayRequest
    ) -> Result[RelayGatewayResult, RelayGatewayError]:
        """Record the call and return the canned status outcome."""
        self.status_calls.append((kind, gateway_job_id, request))
        if self._status_outcome is None:
            return Ok(RelayGatewayResult(status_code=200, headers={}, payload={}))
        return self._status_outcome

class FakeJobPassthroughResolver:
    """Async callable returning the configured fake job passthrough service."""

    def __init__(self, service: FakeJobPassthroughService) -> None:
        self._service = service
        self.calls: list[Any] = []

    async def __call__(self, request: Any) -> FakeJobPassthroughService:
        """Record the request and return the fake service."""
        self.calls.append(request)
        return self._service

class FakeRequest:
    """Minimal request double exposing the state/headers surface endpoints use."""

    def __init__(
        self,
        *,
        body: bytes = b"{}",
        request_id: str | None = None,
        user: dict[str, Any] | None = None,
        path_params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._body = body
        self.state = SimpleNamespace(request_id=request_id, user=user, container=None)
        self.path_params = path_params if path_params is not None else {}
        self.method = "POST"
        self.headers: dict[str, str] = headers if headers is not None else {}

    async def body(self) -> bytes:
        """Return the canned request body."""
        return self._body

class FakeRoute:
    """Minimal route double carrying the path used by the mount guard."""

    def __init__(self, path: str) -> None:
        self.path = path

class FakeApp:
    """Minimal app double recording ``add_route`` registrations."""

    def __init__(self) -> None:
        self.routes: list[FakeRoute] = []
        self.registrations: list[tuple[str, Any, list[str] | None]] = []

    def add_route(
        self, path: str, endpoint: Any, methods: list[str] | None = None
    ) -> None:
        """Record the registration and make it visible to the mount guard."""
        self.registrations.append((path, endpoint, methods))
        self.routes.append(FakeRoute(path))

def _ok_gateway(headers: dict[str, str] | None = None) -> FakeGateway:
    """Build a gateway returning an empty 200 result."""
    return FakeGateway(
        Ok(
            RelayGatewayResult(
                status_code=200,
                headers=headers if headers is not None else {},
                payload={},
            )
        )
    )
