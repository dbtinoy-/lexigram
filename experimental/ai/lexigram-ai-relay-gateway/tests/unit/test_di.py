from structlog.testing import capture_logs

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.di.provider import RelayGatewayProvider
from lexigram.ai.relay.gateway.operations.streams import RelayStreamRegistry
from lexigram.contracts.ai.relay import (
    RelayFormat,
    RelayGatewayProtocol,
    RelayLoss,
    RelayPolicySnapshot,
)
from lexigram.di.container.container import Container
from lexigram.serialization import dumps

REQUEST_ID = "req-1"
TENANT_ID = "tenant-1"
MODEL = "gpt-x"
CHANNEL_NAME = "openai-a"
BASE_URL = "https://up.example"
MARKER = "PAYLOAD_MARKER_9f2"

from ._test_di_support import (
    FakeAuthorizer,
    FakeBilling,
    FakeConverter,
    FakeHTTPClient,
    FakeMediaResolver,
    StaticPolicyStore,
    events_with_name,
    happy_service,
    make_config,
    make_request,
    make_service,
    ok_upstream_response,
)


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


async def test_config_parsed_from_string_boots_di_offline() -> None:
    """A config passed directly as a JSON string wires the provider.

    Config parsing and DI registration make no network, file, or store
    access: the whole boot is driven by one string.
    """
    config_doc = dumps(
        {
            "channels": [
                {
                    "name": CHANNEL_NAME,
                    "upstream_base_url": BASE_URL,
                    "target_format": "CLAUDE",
                    "models": [MODEL],
                    "priority": 1,
                }
            ]
        }
    )
    cfg = RelayGatewayConfig.from_string(config_doc)
    provider = RelayGatewayProvider(
        config=cfg,
        converter=FakeConverter(),
        http_client=FakeHTTPClient(),
    )
    container = Container()
    await provider.register(container)
    resolved = await container.resolve(RelayGatewayConfig)
    registry = await container.resolve(RelayChannelRegistry)
    assert resolved is cfg
    assert resolved.channels[0].name == CHANNEL_NAME
    assert registry.select(RelayFormat.OPENAI_CHAT, MODEL).is_ok()


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
