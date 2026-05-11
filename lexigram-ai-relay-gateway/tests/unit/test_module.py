"""Relay gateway module descriptor, provider metadata, and package export tests.

Covers the finalized ``lexigram.ai.relay.gateway`` package root
(re-exporting the public API), the ``RelayGatewayModule`` descriptor
shape, and an end-to-end wiring of ``RelayGatewayProvider`` through the
real container resolving a working gateway.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.gateway import (
    RelayGatewayConfig,
    RelayGatewayModule,
    RelayGatewayProvider,
    RelayGatewayService,
)
from lexigram.contracts.ai.relay import (
    ClaudeRequest,
    ClaudeResponse,
    ConversionQuality,
    OpenAIChatRequest,
    RelayChannel,
    RelayConvertResult,
    RelayFormat,
    RelayGatewayProtocol,
    RelayGatewayRequest,
)
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.contracts.core.result import Ok
from lexigram.contracts.web import HttpResponse
from lexigram.di.container.container import Container
from lexigram.di.module import DynamicModule, Module
from lexigram.di.provider import Provider
from lexigram.serialization import dumps

REQUEST_ID = "req-1"
TENANT_ID = "tenant-1"
MODEL = "gpt-x"
BASE_URL = "https://up.example"
CHANNEL_NAME = "openai-a"


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


def make_request() -> RelayGatewayRequest:
    """Build a buffered gateway request in Claude wire shape."""
    return RelayGatewayRequest(
        request_id=REQUEST_ID,
        tenant_id=TENANT_ID,
        source=RelayFormat.CLAUDE,
        model=MODEL,
        stream=False,
        payload=ClaudeRequest.from_dict(
            {"model": MODEL, "max_tokens": 1024, "messages": []}
        ).to_dict(),
        headers={},
    )


class FakeConverter:
    """``RelayConverterProtocol`` double returning canned conversions."""

    def convert_request(
        self,
        payload: Any,
        source: RelayFormat,
        target: RelayFormat,
        *,
        context: Any = None,
        registry: Any = None,
    ) -> Any:
        """Return a canned outbound OpenAI Chat request."""
        return Ok(
            RelayConvertResult(
                value=OpenAIChatRequest.from_dict({"model": MODEL}),
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
        """Return a canned inbound Claude response."""
        return Ok(
            RelayConvertResult(
                value=ClaudeResponse.from_dict({"id": "resp-1", "model": MODEL, "content": []}),
                source=source,
                target=target,
                converter_id="test_converter",
                quality=ConversionQuality.GOOD,
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
    """Minimal ``HTTPClientProtocol`` double used by the fixture adapter."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def request(self, **kwargs: Any) -> HttpResponse:
        """Record the call and return a valid OpenAI Chat completions body."""
        self.calls.append(kwargs)
        body = dumps(
            {
                "id": "resp-1",
                "object": "chat.completion",
                "created": 0,
                "model": MODEL,
                "choices": [],
            }
        )
        return HttpResponse(status=200, headers={"content-type": "application/json"}, body=body)


def test_package_exports_public_api() -> None:
    """The package root re-exports the public gateway API."""
    import lexigram.ai.relay.gateway as gateway

    for name in (
        "HTTPUpstreamAdapter",
        "RelayChannelCheckerProtocol",
        "RelayChannelProbeResult",
        "RelayChannelRegistry",
        "RelayGatewayConfig",
        "RelayGatewayModule",
        "RelayGatewayProvider",
        "RelayGatewayService",
        "RelayHealthService",
        "RelayPayloadCodec",
        "UpstreamEventParser",
        "relay_stream",
    ):
        assert name in gateway.__all__
        assert getattr(gateway, name) is not None


def test_gateway_module_is_module() -> None:
    """``RelayGatewayModule`` exists and is decorated."""
    assert issubclass(RelayGatewayModule, Module)


def test_gateway_module_configure_returns_dynamic_module() -> None:
    """``configure()`` returns a ``DynamicModule`` exposing the gateway contract."""
    result = RelayGatewayModule.configure()
    assert isinstance(result, DynamicModule)
    assert result.module is RelayGatewayModule
    assert any(isinstance(provider, RelayGatewayProvider) for provider in result.providers)
    assert RelayGatewayProtocol in result.exports


def test_provider_metadata() -> None:
    """The provider declares stable name and priority."""
    provider = RelayGatewayProvider()
    assert provider.name == "ai-relay-gateway"
    assert provider.priority is ProviderPriority.DOMAIN
    assert isinstance(provider, Provider)


async def test_provider_wires_gateway_into_container() -> None:
    """A provider with injected deps resolves a working gateway."""
    provider = RelayGatewayProvider(
        config=make_config(),
        converter=FakeConverter(),
        http_client=FakeHTTPClient(),
    )
    container = Container()
    await provider.register(container)

    assert container.has(RelayGatewayProtocol)
    assert container.has(RelayGatewayConfig)
    service = await container.resolve(RelayGatewayProtocol)
    assert isinstance(service, RelayGatewayService)
    result = await service.handle(make_request())
    assert result.is_ok()