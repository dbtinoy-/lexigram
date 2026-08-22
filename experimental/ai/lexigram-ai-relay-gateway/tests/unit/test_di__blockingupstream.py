import asyncio

from structlog.testing import capture_logs

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.di.provider import RelayGatewayProvider
from lexigram.ai.relay.gateway.operations.auto_test import RelayChannelAutoTester
from lexigram.ai.relay.gateway.operations.failover import RelayFailoverTracker
from lexigram.ai.relay.gateway.stream import UpstreamEventParser, relay_stream
from lexigram.contracts.ai.relay import (
    RelayConverterProtocol,
    RelayFormat,
    RelayGatewayProtocol,
    UpstreamRequest,
)
from lexigram.contracts.core.health import HealthStatus
from lexigram.contracts.web import HTTPClientProtocol
from lexigram.di.container.container import Container

REQUEST_ID = "req-1"
TENANT_ID = "tenant-1"
MODEL = "gpt-x"
CHANNEL_NAME = "openai-a"
BASE_URL = "https://up.example"
MARKER = "PAYLOAD_MARKER_9f2"

from ._test_di_support import (
    BlockingUpstream,
    FakeConverter,
    FakeHTTPClient,
    FakeSession,
    events_with_name,
    make_channel,
    make_config,
    make_request,
    make_service,
    ok_upstream_response,
)


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


async def test_failover_tracker_bound_and_wired() -> None:
    """Auto-disable wiring binds the tracker and bans a failing channel."""
    provider = RelayGatewayProvider(
        config=RelayGatewayConfig(
            channels=(make_channel(),),
            auto_disable_on_failures=True,
            failover_failure_threshold=1,
        ),
        converter=FakeConverter(),
        http_client=FakeHTTPClient(response=ok_upstream_response(status=502)),
    )
    container = Container()
    await provider.register(container)
    assert container.has(RelayFailoverTracker)
    service = await container.resolve(RelayGatewayProtocol)
    result = await service.handle(make_request())
    assert result.is_err()
    registry = await container.resolve(RelayChannelRegistry)
    assert registry.runtime_enabled() == {CHANNEL_NAME: False}


async def test_failover_absent_when_disabled() -> None:
    """The default config binds no failover tracker."""
    provider = RelayGatewayProvider(config=make_config())
    container = Container()
    await provider.register(container)
    assert container.has(RelayFailoverTracker) is False


async def test_boot_late_binds_container_dependencies() -> None:
    """Boot resolves converter and HTTP client from the container."""
    provider = RelayGatewayProvider(config=make_config())
    container = Container()
    container.singleton(RelayConverterProtocol, FakeConverter())
    container.singleton(
        HTTPClientProtocol, FakeHTTPClient(response=ok_upstream_response())
    )
    await provider.register(container)
    assert container.has(RelayGatewayProtocol) is False
    await provider.boot(container)
    assert container.has(RelayGatewayProtocol)
    service = await container.resolve(RelayGatewayProtocol)
    result = await service.handle(make_request())
    assert result.is_ok()


async def test_boot_without_any_dependencies_stays_unbound() -> None:
    """Boot without converter or HTTP client keeps the gateway unbound."""
    provider = RelayGatewayProvider(config=make_config())
    container = Container()
    await provider.register(container)
    await provider.boot(container)
    assert container.has(RelayGatewayProtocol) is False
