"""Relay gateway DI provider and structured event tests (Relay Gateway plan, Task 7).

Covers ``RelayGatewayProvider`` registration against the real
:class:`~lexigram.di.container.container.Container`, the startup
diagnostic when the converter or HTTP client is missing, injected
dependency wiring (authorizer, media resolver, quota hook), the
structured event stream emitted by ``RelayGatewayService``, the
``relay_gateway_stream_cancelled`` event from ``relay_stream``, and the
provider health check.

Note:
    The framework's structlog pipeline renders through
    ``PrintLoggerFactory``, so ``caplog`` never sees native structlog
    events.  Assertions use ``structlog.testing.capture_logs()``, which
    swaps in a capture factory and restores the global config on exit.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from structlog.testing import capture_logs

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.codec import RelayPayloadCodec
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.di.provider import RelayGatewayProvider
from lexigram.ai.relay.gateway.operations.auto_test import RelayChannelAutoTester
from lexigram.ai.relay.gateway.operations.streams import RelayStreamRegistry
from lexigram.ai.relay.gateway.service import RelayGatewayService
from lexigram.ai.relay.gateway.stream import UpstreamEventParser, relay_stream
from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.governance import (
    RelayBillingProtocol,
    RelayUsageRecord,
    RelayUsageReservation,
    RelayUsageScope,
)
from lexigram.contracts.ai.relay import (
    ClaudeRequest,
    ClaudeResponse,
    ConversionQuality,
    MediaResolverProtocol,
    OpenAIChatRequest,
    OpenAIChatResponse,
    RelayChannel,
    RelayConvertResult,
    RelayConverterProtocol,
    RelayFormat,
    RelayGatewayProtocol,
    RelayGatewayRequest,
    RelayLoss,
    RelayPolicySnapshot,
    RelayPolicyStoreProtocol,
    RelayStreamSessionProtocol,
    RelayUsage,
    UpstreamChunk,
    UpstreamRequest,
)
from lexigram.contracts.auth.guard import AuthorizerProtocol
from lexigram.contracts.core.health import HealthStatus
from lexigram.contracts.core.result import Ok
from lexigram.contracts.web import HTTPClientProtocol, HttpResponse
from lexigram.di.container.container import Container
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


async def test_register_exposes_contracts() -> None:
    """Registering with converter and HTTP client exposes the gateway contracts."""
    provider = RelayGatewayProvider(
        config=make_config(),
        converter=FakeConverter(),
        http_client=FakeHTTPClient(),
    )
    container = Container()
    await provider.register(container)
    assert container.has(RelayGatewayProtocol)
    assert container.has(RelayChannelRegistry)
    assert container.has(RelayGatewayConfig)
    service = await container.resolve(RelayGatewayProtocol)
    assert callable(service.handle)


async def test_stream_registry_is_shared_singleton() -> None:
    """The stream registry resolves as a shared singleton for controls."""
    provider = RelayGatewayProvider(config=make_config())
    container = Container()
    await provider.register(container)
    assert container.has(RelayStreamRegistry)
    first = await container.resolve(RelayStreamRegistry)
    second = await container.resolve(RelayStreamRegistry)
    assert first is second
    handle_id, handle = first.register(
        channel=CHANNEL_NAME, model=MODEL, request_id="req-99"
    )
    assert first.handle(handle_id) is handle


async def test_boot_reconciles_policy_drain_into_selection() -> None:
    """Boot applies a persisted drain to the runtime registry."""
    store = StaticPolicyStore(
        RelayPolicySnapshot(
            enabled_channels={CHANNEL_NAME: False},
            allowed_model_options={CHANNEL_NAME: frozenset({MODEL})},
            media_allowed_schemes=frozenset({"https"}),
            media_allowed_hosts=frozenset(),
            max_request_bytes=1024,
            max_stream_seconds=300.0,
        )
    )
    provider = RelayGatewayProvider(config=make_config(), policy_store=store)
    container = Container()
    await provider.register(container)
    await provider.boot(container)
    registry = await container.resolve(RelayChannelRegistry)
    assert registry.runtime_enabled() == {CHANNEL_NAME: False}
    assert registry.select(RelayFormat.OPENAI_CHAT, MODEL).is_err()


async def test_registered_config_is_configured() -> None:
    """The resolved ``RelayGatewayConfig`` is the one injected into the provider."""
    cfg = make_config()
    provider = RelayGatewayProvider(
        config=cfg,
        converter=FakeConverter(),
        http_client=FakeHTTPClient(),
    )
    container = Container()
    await provider.register(container)
    resolved = await container.resolve(RelayGatewayConfig)
    assert resolved is cfg
    assert resolved.channels[0].name == CHANNEL_NAME


async def test_missing_converter_startup_diagnostic() -> None:
    """Register without a converter logs the diagnostic and skips the gateway."""
    provider = RelayGatewayProvider(config=make_config(), http_client=FakeHTTPClient())
    container = Container()
    with capture_logs() as logs:
        await provider.register(container)
    diagnostics = events_with_name(logs, "relay_gateway_missing_dependency")
    assert len(diagnostics) == 1
    assert "RelayConverterProtocol" in diagnostics[0]["missing"]
    assert container.has(RelayGatewayProtocol) is False


async def test_missing_http_client_startup_diagnostic() -> None:
    """Register without an HTTP client logs the diagnostic and skips the gateway."""
    provider = RelayGatewayProvider(config=make_config(), converter=FakeConverter())
    container = Container()
    with capture_logs() as logs:
        await provider.register(container)
    diagnostics = events_with_name(logs, "relay_gateway_missing_dependency")
    assert len(diagnostics) == 1
    assert "HTTPClientProtocol" in diagnostics[0]["missing"]
    assert container.has(RelayGatewayProtocol) is False


async def test_injected_dependencies_used() -> None:
    """Injected authorizer, media resolver, and billing reach the service."""
    authorizer = FakeAuthorizer()
    media_resolver = FakeMediaResolver()
    billing = FakeBilling()
    converter = FakeConverter()
    provider = RelayGatewayProvider(
        config=make_config(),
        converter=converter,
        http_client=FakeHTTPClient(response=ok_upstream_response()),
        authorizer=authorizer,
        media_resolver=media_resolver,
        billing=billing,
    )
    container = Container()
    await provider.register(container)
    service = await container.resolve(RelayGatewayProtocol)
    result = await service.handle(make_request())
    assert result.is_ok()
    assert authorizer.authorize_calls == [(TENANT_ID, "relay.invoke", MODEL)]
    assert billing.pre_consume_calls == [(REQUEST_ID, TENANT_ID, CHANNEL_NAME)]
    assert billing.settle_statuses == ["completed"]
    assert converter.request_contexts
    assert converter.request_contexts[0].media_resolver is media_resolver
    assert converter.request_contexts[0].channel_name == CHANNEL_NAME


async def test_events_emitted_on_buffered_success() -> None:
    """A successful handle emits the full structured event lifecycle."""
    service, _, _ = happy_service()
    with capture_logs() as logs:
        result = await service.handle(
            make_request(
                headers={"authorization": f"Bearer {MARKER}"},
                payload={"model": MODEL, "marker": MARKER},
            )
        )
    assert result.is_ok()
    names = [entry["event"] for entry in logs]
    for expected in (
        "relay_gateway_request_accepted",
        "relay_gateway_channel_selected",
        "relay_gateway_upstream_started",
        "relay_gateway_request_completed",
    ):
        assert expected in names
    accepted = events_with_name(logs, "relay_gateway_request_accepted")[0]
    assert accepted["request_id"] == REQUEST_ID
    assert accepted["tenant_id"] == TENANT_ID
    assert accepted["source"] == RelayFormat.CLAUDE.value
    assert accepted["model"] == MODEL
    assert accepted["stream"] is False
    selected = events_with_name(logs, "relay_gateway_channel_selected")[0]
    assert selected["request_id"] == REQUEST_ID
    assert selected["channel"] == CHANNEL_NAME
    assert selected["target_format"] == RelayFormat.OPENAI_CHAT.value
    started = events_with_name(logs, "relay_gateway_upstream_started")[0]
    assert started["request_id"] == REQUEST_ID
    assert started["channel"] == CHANNEL_NAME
    assert started["method"] == "POST"
    assert started["url"] == f"{BASE_URL}/v1/chat/completions"
    completed = events_with_name(logs, "relay_gateway_request_completed")[0]
    assert completed["request_id"] == REQUEST_ID
    assert completed["tenant_id"] == TENANT_ID
    assert completed["channel"] == CHANNEL_NAME
    assert completed["source"] == RelayFormat.CLAUDE.value
    assert completed["target"] == RelayFormat.OPENAI_CHAT.value
    assert completed["status_code"] == 200
    assert completed["code"] == "OK"
    assert completed["duration_ms"] >= 0.0
    assert completed["loss_codes"] == ()
    for entry in logs:
        assert MARKER not in repr(entry)


async def test_conversion_loss_event() -> None:
    """Conversion losses are surfaced as a structured loss event."""
    converter = FakeConverter(
        losses=(
            RelayLoss(
                field="thinking",
                target=RelayFormat.CLAUDE,
                reason="no_thinking",
            ),
        )
    )
    http_client = FakeHTTPClient(response=ok_upstream_response())
    service = make_service(converter, http_client)
    with capture_logs() as logs:
        result = await service.handle(make_request())
    assert result.is_ok()
    loss_events = events_with_name(logs, "relay_gateway_conversion_loss")
    assert len(loss_events) == 1
    assert loss_events[0]["request_id"] == REQUEST_ID
    assert loss_events[0]["converter_id"] == "test_converter"
    assert loss_events[0]["loss_codes"] == ("no_thinking",)
    completed = events_with_name(logs, "relay_gateway_request_completed")[0]
    assert completed["loss_codes"] == ("no_thinking",)


async def test_upstream_failed_event() -> None:
    """A non-2xx upstream response emits failed and completed events."""
    service = make_service(
        FakeConverter(),
        FakeHTTPClient(response=ok_upstream_response(status=429)),
    )
    with capture_logs() as logs:
        result = await service.handle(make_request())
    assert result.is_err()
    assert result.unwrap_err().code == "UPSTREAM_ERROR"
    failed = events_with_name(logs, "relay_gateway_upstream_failed")
    assert len(failed) == 1
    assert failed[0]["request_id"] == REQUEST_ID
    assert failed[0]["channel"] == CHANNEL_NAME
    assert failed[0]["code"] == "UPSTREAM_ERROR"
    assert failed[0]["status_code"] == 429
    completed = events_with_name(logs, "relay_gateway_request_completed")[0]
    assert completed["code"] == "UPSTREAM_ERROR"
    assert completed["status_code"] == 429
    assert completed["channel"] == CHANNEL_NAME


async def test_stream_cancelled_event() -> None:
    """Closing a stream mid-flight cancels upstream once and logs the event."""
    block = asyncio.Event()
    upstream = BlockingUpstream(block)
    session = FakeSession()
    parser = UpstreamEventParser(
        session=session,
        source=RelayFormat.OPENAI_CHAT,
        request_id=REQUEST_ID,
    )
    request = UpstreamRequest(
        request_id=REQUEST_ID,
        method="POST",
        url=f"{BASE_URL}/v1/chat/completions",
        headers={},
        payload={"model": MODEL},
        timeout_seconds=60.0,
    )
    with capture_logs() as logs:
        generator = relay_stream(upstream, request, parser)
        first = await anext(generator)
        assert first is not None
        await generator.aclose()
    cancelled = events_with_name(logs, "relay_gateway_stream_cancelled")
    assert len(cancelled) == 1
    assert cancelled[0]["request_id"] == REQUEST_ID
    assert upstream.cancel_calls == 1


async def test_health_check() -> None:
    """The provider reports itself as healthy."""
    provider = RelayGatewayProvider()
    result = await provider.health_check()
    assert result.status == HealthStatus.HEALTHY
    assert result.component == "ai-relay-gateway"


async def test_auto_tester_started_when_enabled() -> None:
    """With ``auto_test_channels=True`` boot starts the tester and shutdown stops it."""
    provider = RelayGatewayProvider(
        config=RelayGatewayConfig(
            channels=(make_channel(),),
            auto_test_channels=True,
            auto_test_interval_seconds=30,
        )
    )
    container = Container()
    await provider.register(container)
    tester = await container.resolve(RelayChannelAutoTester)
    assert tester.is_running is False
    await provider.boot(container)
    assert tester.is_running is True
    await provider.shutdown()
    assert tester.is_running is False


async def test_auto_tester_absent_when_disabled() -> None:
    """With the default config the provider never creates a tester."""
    provider = RelayGatewayProvider(config=make_config())
    container = Container()
    await provider.register(container)
    assert container.has(RelayChannelAutoTester) is False
    await provider.boot(container)
    await provider.shutdown()


async def test_register_twice_behavior() -> None:
    """Re-registering the same provider overwrites bindings without raising.

    The container's ``ServiceStore`` overwrites duplicate descriptors, so
    the second register call succeeds and the gateway stays resolvable.
    """
    provider = RelayGatewayProvider(
        config=make_config(),
        converter=FakeConverter(),
        http_client=FakeHTTPClient(response=ok_upstream_response()),
    )
    container = Container()
    await provider.register(container)
    await provider.register(container)
    assert container.has(RelayGatewayProtocol)
    service = await container.resolve(RelayGatewayProtocol)
    result = await service.handle(make_request())
    assert result.is_ok()
