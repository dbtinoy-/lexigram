"""Shared doubles and fixtures for the passthrough test modules.

Mirrors the ``service_test_helpers`` pattern: the package conftest puts
``tests/unit`` on ``sys.path`` so this module is imported by its bare
name from every passthrough test module.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.passthrough import (
    PassthroughService,
    RelayPassthroughBody,
)
from lexigram.contracts.ai.governance import (
    RelayBillingError,
    RelayUsageRecord,
    RelayUsageReservation,
    RelayUsageScope,
)
from lexigram.contracts.ai.relay import (
    RelayChannel,
    RelayFormat,
    RelayGatewayError,
    RelayGatewayRequest,
    RelayUsage,
    UpstreamRequest,
    UpstreamResponse,
)
from lexigram.contracts.core.result import Err, Ok, Result

KIND = "embeddings"
MODEL = "text-embedding-3-small"
REQUEST_ID = "req-123"
TENANT_ID = "tenant-1"
BASE_URL = "https://upstream.example.com"
WHITESPACE_BODY = {"model": MODEL, "input": ["hello"], "encoding_format": "float"}

MULTIPART_BOUNDARY = "bnd-42"
MULTIPART_CONTENT_TYPE = f"multipart/form-data; boundary={MULTIPART_BOUNDARY}"
MULTIPART_BODY = b"".join(
    [
        f"--{MULTIPART_BOUNDARY}\r\n".encode("ascii"),
        b'Content-Disposition: form-data; name="model"\r\n',
        b"\r\n",
        MODEL.encode("ascii"),
        b"\r\n",
        f"--{MULTIPART_BOUNDARY}\r\n".encode("ascii"),
        b'Content-Disposition: form-data; name="image"; filename="starry.png"\r\n',
        b"Content-Type: image/png\r\n",
        b"\r\n",
        b"\x89PNG\r\n\x1a\nBINARY\x00\xffDATA",
        b"\r\n",
        f"--{MULTIPART_BOUNDARY}--\r\n".encode("ascii"),
    ]
)
"""A two-part multipart body: a ``model`` field plus a binary ``image`` part."""


def make_channel(name: str = "a", **overrides: Any) -> RelayChannel:
    """Build an embeddings-capable channel with defaults; ``overrides`` win."""
    defaults: dict[str, Any] = {
        "name": name,
        "upstream_base_url": BASE_URL,
        "target_format": RelayFormat.OPENAI_CHAT,
        "models": (MODEL,),
        "endpoint_kinds": frozenset({"embeddings"}),
    }
    defaults.update(overrides)
    return RelayChannel(**defaults)


def default_channels() -> tuple[RelayChannel, ...]:
    """One enabled embeddings channel plus one disabled channel."""
    return (make_channel("a"), make_channel("b", enabled=False))


def make_request(
    model: str = MODEL,
    payload: RelayPassthroughBody | dict[str, Any] | None = None,
    channel: RelayChannel | None = None,
) -> RelayGatewayRequest:
    """Build a passthrough ``RelayGatewayRequest`` with an embeddings body."""
    return RelayGatewayRequest(
        request_id=REQUEST_ID,
        tenant_id=TENANT_ID,
        source=RelayFormat.OPENAI_CHAT,
        model=model,
        stream=False,
        payload=payload if payload is not None else dict(WHITESPACE_BODY),
        headers={},
        channel=channel,
    )


def ok_binary_upstream(
    body: bytes,
    content_type: str,
    status_code: int = 200,
) -> Result[UpstreamResponse, RelayGatewayError]:
    """A canned Ok binary upstream result."""
    return Ok(
        UpstreamResponse(
            status_code=status_code,
            headers={"content-type": content_type},
            payload=body,
        )
    )


def ok_upstream(
    payload: dict[str, Any] | None,
    status_code: int = 200,
) -> Result[UpstreamResponse, RelayGatewayError]:
    """A canned Ok upstream result."""
    return Ok(
        UpstreamResponse(
            status_code=status_code,
            headers={"content-type": "application/json"},
            payload=payload,
        )
    )


class RecordingRegistry(RelayChannelRegistry):
    """``RelayChannelRegistry`` double that records ``select_for_endpoint`` calls."""

    def __init__(
        self, config: RelayGatewayConfig, calls: list[tuple[Any, ...]]
    ) -> None:
        super().__init__(config)
        self.calls = calls

    def select_for_endpoint(
        self,
        kind: str,
        model: str,
        *,
        exclude: frozenset[str] = frozenset(),
    ) -> Result[RelayChannel, RelayGatewayError]:
        """Record the call and delegate to the real selection logic."""
        self.calls.append(("select_endpoint", kind, model))
        return super().select_for_endpoint(kind, model, exclude=exclude)


class RecordingAuthorizer:
    """``AuthorizerProtocol`` double that records ``authorize`` calls."""

    def __init__(self, calls: list[tuple[Any, ...]], allowed: bool = True) -> None:
        self.calls = calls
        self.allowed = allowed

    async def authorize(self, user: Any, action: str, resource: Any) -> bool:
        """Record the call and return the configured verdict."""
        self.calls.append(("authorize", user, action, resource))
        return self.allowed


class RecordingUpstream:
    """``HTTPUpstreamAdapter`` double that records upstream calls."""

    def __init__(
        self,
        calls: list[tuple[Any, ...]],
        *,
        result: Result[UpstreamResponse, RelayGatewayError] | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.calls = calls
        self.result = result
        self.error = error

    async def request(
        self, request: UpstreamRequest
    ) -> Result[UpstreamResponse, RelayGatewayError]:
        """Record the call; return the canned result or raise the error."""
        self.calls.append(("upstream", request.url))
        if self.error is not None:
            raise self.error
        if self.result is None:
            raise AssertionError("RecordingUpstream needs a result or an error")
        return self.result


class RecordingBilling:
    """``RelayBillingProtocol`` double recording lifecycle invocations."""

    def __init__(
        self,
        calls: list[tuple[Any, ...]],
        *,
        admit: bool = True,
    ) -> None:
        self.calls = calls
        self.admit = admit
        self.settle_statuses: list[str] = []
        self.settle_usages: list[RelayUsage | None] = []
        self.settled_usages: list[RelayUsage | None] = []

    async def pre_consume(
        self,
        request_id: str,
        scope: RelayUsageScope,
        payload: Any,
    ) -> Any:
        """Record the admission attempt; return the canned reservation."""
        self.calls.append(("pre_consume", scope.tenant_id, scope.channel))
        if not self.admit:
            return Err(
                RelayBillingError(
                    code="quota_exhausted",
                    message="quota exhausted",
                    request_id=request_id,
                    tenant_id=scope.tenant_id,
                )
            )
        return Ok(
            RelayUsageReservation(
                reservation_id=f"res-{request_id}",
                request_id=request_id,
                estimated_tokens=10,
                estimated_charge=Decimal("0.01"),
                expires_at=datetime.now(UTC) + timedelta(seconds=60),
            )
        )

    async def settle(
        self,
        reservation: RelayUsageReservation,
        result: Any,
        *,
        status: str,
    ) -> Any:
        """Record the settlement status and usage; return a canned record."""
        self.calls.append(("settle", status))
        self.settle_statuses.append(status)
        self.settle_usages.append(result.usage)
        return Ok(
            RelayUsageRecord(
                request_id=reservation.request_id,
                attempt_id="attempt-1",
                scope=RelayUsageScope(tenant_id="tenant-1"),
                usage=RelayUsage(),
                charge=Decimal(0),
                currency="USD",
                status=status,
            )
        )

    async def release(self, reservation: RelayUsageReservation) -> None:
        """Record the release of a reservation."""
        self.calls.append(("release", reservation.request_id))


class FailingSettling(RecordingBilling):
    """Billing double whose settlement always fails."""

    async def settle(
        self,
        reservation: RelayUsageReservation,
        result: Any,
        *,
        status: str,
    ) -> Any:
        """Record the attempt and return a billing error."""
        self.calls.append(("settle", status))
        self.settle_statuses.append(status)
        return Err(
            RelayBillingError(
                code="billing_store_unavailable",
                message="store unavailable",
                request_id=reservation.request_id,
            )
        )


def default_upstream_response() -> dict[str, Any]:
    """A canned OpenAI-shaped embeddings response body."""
    return {
        "object": "list",
        "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}],
        "model": MODEL,
        "usage": {"prompt_tokens": 5, "total_tokens": 5},
    }


def make_service(
    calls: list[tuple[Any, ...]],
    *,
    channels: tuple[RelayChannel, ...] | None = None,
    model_suffix: dict[str, str] | None = None,
    upstream: RecordingUpstream | None = None,
    authorizer: RecordingAuthorizer | None = None,
    billing: RecordingBilling | None = None,
) -> PassthroughService:
    """Assemble a passthrough service wired to recording doubles."""
    config = RelayGatewayConfig(
        channels=channels if channels is not None else default_channels(),
        model_suffix=model_suffix or {},
    )
    return PassthroughService(
        registry=RecordingRegistry(config, calls),
        upstream=upstream
        or RecordingUpstream(calls, result=ok_upstream(default_upstream_response())),
        config=config,
        authorizer=authorizer,
        billing=billing,
    )


class RequestCapturingUpstream:
    """Upstream double that captures the resolved ``UpstreamRequest``."""

    def __init__(
        self,
        calls: list[tuple[Any, ...]],
        *,
        result: Result[UpstreamResponse, RelayGatewayError] | None = None,
    ) -> None:
        self.calls = calls
        self.captured: UpstreamRequest | None = None
        self.result = result

    async def request(
        self, request: UpstreamRequest
    ) -> Result[UpstreamResponse, RelayGatewayError]:
        """Record the request; return the canned result."""
        self.calls.append(("upstream", request.url))
        self.captured = request
        if self.result is not None:
            return self.result
        return ok_upstream(
            {
                "object": "list",
                "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}],
                "model": MODEL,
                "usage": {"prompt_tokens": 5, "total_tokens": 5},
            }
        )