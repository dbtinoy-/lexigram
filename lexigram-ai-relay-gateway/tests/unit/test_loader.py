"""Tests for durable-channel boot reconciliation in the gateway provider."""

from __future__ import annotations

import pytest

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.di.provider import RelayGatewayProvider
from lexigram.ai.relay.gateway.loader import DurableChannelLoader
from lexigram.contracts.ai.relay import (
    RelayChannel,
    RelayChannelSnapshot,
    RelayChannelStoreProtocol,
    RelayFormat,
    RelayPolicySnapshot,
)
from lexigram.di.container.container import Container

BASE_URL = "https://up.example"
MODEL = "gpt-x"


def make_channel(name: str, *, priority: int = 1, enabled: bool = True) -> RelayChannel:
    """Build a RelayChannel on a stable test base URL."""
    return RelayChannel(
        name=name,
        upstream_base_url=BASE_URL,
        target_format=RelayFormat.OPENAI_CHAT,
        models=(MODEL,),
        priority=priority,
        enabled=enabled,
    )


class FakeChannelStore(RelayChannelStoreProtocol):
    """In-memory store double for loader tests."""

    def __init__(self, snapshots: list[RelayChannelSnapshot]) -> None:
        self.snapshots = snapshots

    async def list_channels(self) -> list[RelayChannelSnapshot]:
        return list(self.snapshots)

    async def upsert(
        self, channel: RelayChannel, *, expected_revision: int | None = None
    ) -> int | None:
        raise NotImplementedError

    async def delete(self, name: str, *, expected_revision: int) -> bool:
        raise NotImplementedError


def snapshot(channel: RelayChannel, revision: int = 1) -> RelayChannelSnapshot:
    """Wrap a channel in a snapshot with plausible timestamps."""
    return RelayChannelSnapshot(
        channel=channel,
        revision=revision,
        created_at="2026-08-10T00:00:00+00:00",
        updated_at="2026-08-10T00:00:00+00:00",
    )


async def test_loader_returns_static_unchanged_when_store_empty() -> None:
    static = (make_channel("c1"), make_channel("c2"))
    loader = DurableChannelLoader(FakeChannelStore([]))
    merged = await loader.load(static)
    assert merged == static


async def test_loader_store_rows_override_static_names() -> None:
    static = (make_channel("c1", priority=1),)
    store_rows = [snapshot(make_channel("c1", priority=99))]
    loader = DurableChannelLoader(FakeChannelStore(store_rows))
    merged = await loader.load(static)
    assert [ch.name for ch in merged] == ["c1"]
    assert merged[0].priority == 99


async def test_loader_appends_store_only_channels() -> None:
    static = (make_channel("c1"),)
    store_rows = [
        snapshot(make_channel("c2")),
        snapshot(make_channel("c3", priority=5, enabled=False)),
    ]
    loader = DurableChannelLoader(FakeChannelStore(store_rows))
    merged = await loader.load(static)
    assert [ch.name for ch in merged] == ["c1", "c2", "c3"]
    assert merged[2].enabled is False


async def test_loader_rejects_duplicate_names_from_store() -> None:
    static = ()
    duplicates = [snapshot(make_channel("dup")), snapshot(make_channel("dup"))]
    loader = DurableChannelLoader(FakeChannelStore(duplicates))
    with pytest.raises(ValueError, match="duplicate channel name"):
        await loader.load(static)


async def test_provider_boot_reconciles_registry_from_store() -> None:
    provider = RelayGatewayProvider(config=RelayGatewayConfig(channels=(make_channel("c1"),)))
    container = Container()
    await provider.register(container)
    container.singleton(
        RelayChannelStoreProtocol,
        FakeChannelStore(
            [snapshot(make_channel("c1", priority=77)), snapshot(make_channel("c2"))]
        ),
    )
    await provider.boot(container)
    registry = await container.resolve(RelayChannelRegistry)
    assert [ch.name for ch in registry.channels] == ["c1", "c2"]
    assert registry.channels[0].priority == 77


async def test_provider_boot_keeps_static_without_store() -> None:
    static = (make_channel("c1"),)
    provider = RelayGatewayProvider(config=RelayGatewayConfig(channels=static))
    container = Container()
    await provider.register(container)
    await provider.boot(container)
    registry = await container.resolve(RelayChannelRegistry)
    assert registry.channels == static


async def test_provider_boot_still_drains_policy_disabled_channels() -> None:
    from lexigram.ai.relay.gateway.operations.controls import (
        InMemoryRelayPolicyStore,
    )

    policy = InMemoryRelayPolicyStore.with_defaults(
        RelayGatewayConfig(channels=(make_channel("c1"),))
    )
    await policy.save(
        RelayPolicySnapshot(
            enabled_channels={"c1": False},
            allowed_model_options={},
            media_allowed_schemes=frozenset({"https"}),
            media_allowed_hosts=frozenset(),
            max_request_bytes=1024,
            max_stream_seconds=300.0,
        )
    )
    provider = RelayGatewayProvider(
        config=RelayGatewayConfig(channels=(make_channel("c1"),)),
        policy_store=policy,
    )
    container = Container()
    await provider.register(container)
    container.singleton(
        RelayChannelStoreProtocol, FakeChannelStore([])
    )
    await provider.boot(container)
    registry = await container.resolve(RelayChannelRegistry)
    assert registry.channels[0].name == "c1"
    assert registry.runtime_enabled() == {"c1": False}