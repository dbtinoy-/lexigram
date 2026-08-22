"""Shared fixtures/stubs for test_di tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.codec import RelayPayloadCodec
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.service import RelayGatewayService
from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.contracts.ai.governance import (
    RelayUsageRecord,
    RelayUsageReservation,
    RelayUsageScope,
)
from lexigram.contracts.ai.relay import (
    ClaudeRequest,
    ClaudeResponse,
    ConversionQuality,
    OpenAIChatRequest,
    RelayChannel,
    RelayConvertResult,
    RelayFormat,
    RelayGatewayRequest,
    RelayLoss,
    RelayPolicySnapshot,
    RelayPolicyStoreProtocol,
    RelayUsage,
    UpstreamChunk,
    UpstreamRequest,
)
from lexigram.contracts.core.result import Ok
from lexigram.contracts.web import HttpResponse
from lexigram.serialization import dumps

REQUEST_ID = "req-1"
TENANT_ID = "tenant-1"
MODEL = "gpt-x"
CHANNEL_NAME = "openai-a"
BASE_URL = "https://up.example"
MARKER = "PAYLOAD_MARKER_9f2"


def make_channel() -> RelayChannel:
    """The fixture channel: OpenAI Chat target on a stable test base URL."""
    return RelayChannel(
        name=CHANNEL_NAME,
        upstream_base_url=BASE_URL,
        target_format=RelayFormat.OPENAI_CHAT,
        models=(MODEL,),
        priority=1,
    )


def make_config() -> RelayGatewayConfig:
    """The fixture gateway configuration with exactly one enabled channel."""
    return RelayGatewayConfig(channels=(make_channel(),))


def make_request(
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
) -> RelayGatewayRequest:
    """Build a buffered gateway request in Claude wire shape."""
    return RelayGatewayRequest(
        request_id=REQUEST_ID,
        tenant_id=TENANT_ID,
        source=RelayFormat.CLAUDE,
        model=MODEL,
        stream=False,
        payload=payload
        if payload is not None
        else ClaudeRequest.from_dict(
            {"model": MODEL, "max_tokens": 1024, "messages": []}
        ).to_dict(),
        headers=headers if headers is not None else {},
    )


def openai_request_dto() -> OpenAIChatRequest:
    """The converted outbound request DTO for the OpenAI Chat target."""
    return OpenAIChatRequest.from_dict({"model": MODEL})


def openai_response_wire() -> dict[str, Any]:
    """A minimal OpenAI Chat completions response wire body."""
    return {
        "id": "resp-1",
        "object": "chat.completion",
        "created": 0,
        "model": MODEL,
        "choices": [],
    }


def claude_response_dto() -> ClaudeResponse:
    """The converted inbound response DTO for the Claude source."""
    return ClaudeResponse.from_dict({"id": "resp-1", "model": MODEL, "content": []})


def ok_upstream_response(status: int = 200) -> HttpResponse:
    """An ``HttpResponse`` with a valid OpenAI Chat body for *status*."""
    body = (
        dumps(openai_response_wire())
        if status == 200
        else dumps({"error": {"message": "rate limited"}})
    )
    return HttpResponse(
        status=status, headers={"content-type": "application/json"}, body=body
    )


class StaticPolicyStore(RelayPolicyStoreProtocol):
    """In-memory policy store seeded with a fixed snapshot."""

    def __init__(self, snapshot: RelayPolicySnapshot) -> None:
        self.current = snapshot

    async def load(self) -> RelayPolicySnapshot:
        return self.current

    async def save(self, snapshot: RelayPolicySnapshot) -> None:
        self.current = snapshot


class FakeConverter:
    """``RelayConverterProtocol`` double returning canned conversions.

    Records the last ``RelayConversionContext`` seen per phase so tests
    can assert host wiring (media resolver, channel, request id).
    """

    def __init__(
        self,
        *,
        losses: tuple[RelayLoss, ...] = (),
        warnings: tuple[str, ...] = (),
    ) -> None:
        self.losses = losses
        self.warnings = warnings
        self.request_contexts: list[Any] = []
        self.response_contexts: list[Any] = []

    def convert_request(
        self,
        payload: Any,
        source: RelayFormat,
        target: RelayFormat,
        *,
        context: Any = None,
        registry: Any = None,
    ) -> Any:
        """Record the context and return the canned request conversion."""
        self.request_contexts.append(context)
        return Ok(
            RelayConvertResult(
                value=openai_request_dto(),
                source=source,
                target=target,
                converter_id="test_converter",
                quality=ConversionQuality.GOOD,
            )
        )

    def convert_response(
        self,
        payload: Any,
        source: RelayFormat,
        target: RelayFormat,
        *,
        context: Any = None,
        registry: Any = None,
    ) -> Any:
        """Record the context and return the canned response conversion."""
        self.response_contexts.append(context)
        return Ok(
            RelayConvertResult(
                value=claude_response_dto(),
                source=source,
                target=target,
                converter_id="test_converter",
                quality=ConversionQuality.GOOD,
                losses=self.losses,
                warnings=self.warnings,
            )
        )

    def new_stream_session(
        self,
        source: RelayFormat,
        target: RelayFormat,
        *,
        options: Any = None,
        context: Any = None,
        registry: Any = None,
    ) -> Any:
        """Unused by buffered tests."""
        raise NotImplementedError("new_stream_session is unused by buffered tests")

    def convert_stream_chunk(self, session: Any, event: Any) -> tuple[Any, ...]:
        """Unused by buffered tests."""
        raise NotImplementedError("convert_stream_chunk is unused by buffered tests")

    def finalize(self, session: Any) -> tuple[Any, ...]:
        """Unused by buffered tests."""
        raise NotImplementedError("finalize is unused by buffered tests")


class FakeHTTPClient:
    """``HTTPClientProtocol`` double returning the canned response.

    Implements every protocol member (start/stop/request plus the verb
    shortcuts) so container protocol validation accepts it.
    """

    def __init__(self, response: HttpResponse | None = None) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def _dispatch(self, method: str, url: str, **kwargs: Any) -> HttpResponse:
        """Record the call and return the canned response."""
        self.calls.append({"method": method, "url": url, **kwargs})
        if self.response is None:
            raise AssertionError("FakeHTTPClient needs a response")
        return self.response

    async def start(self) -> None:
        """No-op start."""

    async def stop(self) -> None:
        """No-op stop."""

    async def request(self, method: str, url: str, **kwargs: Any) -> HttpResponse:
        """Perform an arbitrary request."""
        return await self._dispatch(method, url, **kwargs)

    async def get(self, url: str, **kwargs: Any) -> HttpResponse:
        """Perform GET."""
        return await self._dispatch("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> HttpResponse:
        """Perform POST."""
        return await self._dispatch("POST", url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> HttpResponse:
        """Perform PUT."""
        return await self._dispatch("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> HttpResponse:
        """Perform DELETE."""
        return await self._dispatch("DELETE", url, **kwargs)

    async def patch(self, url: str, **kwargs: Any) -> HttpResponse:
        """Perform PATCH."""
        return await self._dispatch("PATCH", url, **kwargs)

    async def head(self, url: str, **kwargs: Any) -> HttpResponse:
        """Perform HEAD."""
        return await self._dispatch("HEAD", url, **kwargs)


class FakeAuthorizer:
    """``AuthorizerProtocol`` double recording ``authorize`` calls."""

    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.authorize_calls: list[tuple[Any, ...]] = []

    async def authorize(self, user: Any, action: str, resource: Any) -> bool:
        """Record the call and return the configured verdict."""
        self.authorize_calls.append((user, action, resource))
        return self.allowed

    async def check_access(
        self,
        user: Any,
        allowed_roles: set[str],
        resource: str | None = None,
        action: str | None = None,
    ) -> bool:
        """Unused by gateway tests."""
        raise NotImplementedError("check_access is unused by gateway tests")

    async def can(self, user: Any, action: str, resource: str) -> bool:
        """Unused by gateway tests."""
        raise NotImplementedError("can is unused by gateway tests")


class FakeMediaResolver:
    """``MediaResolverProtocol`` double; buffered tests never resolve."""

    def resolve(self, url: str) -> Any:
        """Never called by buffered tests."""
        raise NotImplementedError("resolve is unused by buffered tests")


class FakeBilling:
    """``RelayBillingProtocol`` double recording the lifecycle calls."""

    def __init__(self) -> None:
        self.pre_consume_calls: list[tuple[str, str, str]] = []
        self.settle_statuses: list[str] = []
        self.release_count = 0

    async def pre_consume(
        self,
        request_id: str,
        scope: Any,
        payload: Any,
    ) -> Any:
        """Record the scope and return a canned reservation."""
        self.pre_consume_calls.append((request_id, scope.tenant_id, scope.channel))
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
        reservation: Any,
        result: Any,
        *,
        status: str,
    ) -> Any:
        """Record the settle status and return a canned record."""
        self.settle_statuses.append(status)
        return Ok(
            RelayUsageRecord(
                request_id=reservation.request_id,
                attempt_id="attempt-1",
                scope=RelayUsageScope(tenant_id=TENANT_ID),
                usage=RelayUsage(),
                charge=Decimal(0),
                currency="USD",
                status=status,
            )
        )

    async def release(self, reservation: Any) -> None:
        """Record the release of a reservation."""
        self.release_count += 1


class FakeSession:
    """Minimal ``RelayStreamSessionProtocol`` double echoing accepted events."""

    def __init__(self) -> None:
        self.accepted: list[Any] = []

    def accept(self, event: Any) -> tuple[Any, ...]:
        """Record and echo the event."""
        self.accepted.append(event)
        return (event,)

    def finalize(self) -> tuple[Any, ...]:
        """Return no terminal events."""
        return ()

    def snapshot(self) -> Any:
        """Return ``None``; state is read through ``accepted``."""
        return None


class BlockingUpstream:
    """``RelayUpstreamProtocol`` double: one chunk, then block forever."""

    def __init__(self, block: asyncio.Event) -> None:
        self.block = block
        self.cancel_calls = 0

    async def stream(self, request: UpstreamRequest) -> AsyncIterator[UpstreamChunk]:
        """Yield one chunk, then block until released."""
        yield UpstreamChunk(
            event="chat.completion.chunk",
            data=dumps(
                {
                    "id": "chatcmpl-1",
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": MODEL,
                    "choices": [
                        {"index": 0, "delta": {"content": "hi"}, "finish_reason": None}
                    ],
                }
            ).decode("utf-8"),
        )
        await self.block.wait()

    async def cancel(self, request_id: str) -> None:
        """Record the cancel call."""
        self.cancel_calls += 1

    async def request(self, request: UpstreamRequest) -> Any:
        """Unused by the streaming path."""
        raise AssertionError("BlockingUpstream.request is unused by streaming tests")


def make_service(
    converter: FakeConverter,
    http_client: FakeHTTPClient,
    *,
    authorizer: FakeAuthorizer | None = None,
    media_resolver: FakeMediaResolver | None = None,
    billing: FakeBilling | None = None,
) -> RelayGatewayService:
    """Assemble a service over the fakes, mirroring test_service wiring."""
    return RelayGatewayService(
        converter=converter,
        codec=RelayPayloadCodec(),
        registry=RelayChannelRegistry(make_config()),
        upstream=HTTPUpstreamAdapter(http_client),
        config=make_config(),
        authorizer=authorizer,
        media_resolver=media_resolver,
        billing=billing,
    )


def events_with_name(logs: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    """Return every captured event with the given event name."""
    return [entry for entry in logs if entry.get("event") == name]


def happy_service() -> tuple[RelayGatewayService, FakeHTTPClient, FakeConverter]:
    """A service whose fakes all return success on the happy path."""
    converter = FakeConverter()
    http_client = FakeHTTPClient(response=ok_upstream_response())
    return make_service(converter, http_client), http_client, converter


__all__ = [
    "BlockingUpstream",
    "FakeAuthorizer",
    "FakeBilling",
    "FakeConverter",
    "FakeHTTPClient",
    "FakeMediaResolver",
    "FakeSession",
    "StaticPolicyStore",
    "claude_response_dto",
    "events_with_name",
    "happy_service",
    "make_channel",
    "make_config",
    "make_request",
    "make_service",
    "ok_upstream_response",
    "openai_request_dto",
    "openai_response_wire",
]
