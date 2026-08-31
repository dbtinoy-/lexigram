from __future__ import annotations

import pytest

from lexigram.contracts.web.sse import ReactiveSseBridgeProtocol
from lexigram.di.container import Container
from lexigram.web.di import provider_sections
from lexigram.web.di.provider import WebProvider
from lexigram.web.transport.reactive import sse_from_stream


@pytest.mark.asyncio
async def test_reactive_sse_bridge_resolves_to_bridge_callable() -> None:
    """The DI registration must not eagerly consume a stream argument."""
    container = Container()
    provider_sections.register_transport_services(WebProvider(), container)

    bridge = await container.resolve(ReactiveSseBridgeProtocol)

    assert bridge is sse_from_stream
