"""Tests for relay channel CRUD and test admin actions and page."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay.gateway.admin import actions as relay_actions
from lexigram.ai.relay.gateway.admin.contributor import (
    RelayGatewayAdminContributor,
)
from lexigram.ai.relay.gateway.admin.pages import RelayGatewayChannelsPage
from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.operations.controls import (
    PERMISSION_CHANNEL_MANAGE,
)
from lexigram.ai.relay.gateway.operations.health import (
    RelayChannelProbeResult,
    RelayHealthService,
)
from lexigram.contracts.ai.relay import (
    RelayChannel,
    RelayChannelSnapshot,
    RelayChannelStoreProtocol,
    RelayFormat,
)
from lexigram.di.container.container import Container

BASE_URL = "https://up.example"
MODEL = "gpt-x"

_ACTION_NAMES = ("create_channel", "update_channel", "delete_channel", "test_channel")


def make_channel(
    name: str, *, priority: int = 1, enabled: bool = True
) -> RelayChannel:
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
    """In-memory store double with working revision CAS."""

    def __init__(self, snapshots: list[RelayChannelSnapshot] | None = None) -> None:
        self.rows: dict[str, RelayChannelSnapshot] = {
            s.channel.name: s for s in (snapshots or [])
        }

    async def list_channels(self) -> list[RelayChannelSnapshot]:
        return list(self.rows.values())

    async def upsert(
        self, channel: RelayChannel, *, expected_revision: int | None = None
    ) -> int | None:
        existing = self.rows.get(channel.name)
        if existing is None:
            if expected_revision is not None:
                return None
            self.rows[channel.name] = RelayChannelSnapshot(
                channel=channel,
                revision=1,
                created_at="2026-08-10T00:00:00+00:00",
                updated_at="2026-08-10T00:00:00+00:00",
            )
            return 1
        if expected_revision is not None and expected_revision != existing.revision:
            return None
        new_revision = existing.revision + 1
        self.rows[channel.name] = RelayChannelSnapshot(
            channel=channel,
            revision=new_revision,
            created_at=existing.created_at,
            updated_at=existing.updated_at,
        )
        return new_revision

    async def delete(self, name: str, *, expected_revision: int) -> bool:
        existing = self.rows.get(name)
        if existing is None or existing.revision != expected_revision:
            return False
        del self.rows[name]
        return True


class FakeChecker:
    """Bounded probe stub returning a healthy verdict."""

    async def check(self, channel: RelayChannel) -> RelayChannelProbeResult:
        return RelayChannelProbeResult(ok=True, latency_ms=12.0)


def make_container(store: FakeChannelStore, health: Any = None) -> Container:
    """Build a container with the store (and optionally health) bound."""
    container = Container()
    container.singleton(RelayChannelStoreProtocol, store)
    if health is not None:
        container.singleton(RelayHealthService, health)
    return container


def make_health(channel: RelayChannel = make_channel("c1")) -> RelayHealthService:
    """Build a health service probing one channel."""
    registry = RelayChannelRegistry(RelayGatewayConfig(channels=(channel,)))
    return RelayHealthService(registry=registry, checker=FakeChecker())


def default_params(name: str, **overrides: object) -> dict[str, object]:
    """Build a valid channel payload dict for the CRUD actions."""
    params: dict[str, object] = {
        "name": name,
        "upstream_base_url": BASE_URL,
        "target_format": "openai_chat",
        "models": [MODEL],
        "priority": 1,
        "weight": 100,
        "enabled": True,
        "timeout_seconds": 60.0,
    }
    params.update(overrides)
    return params


class TestPermissions:
    def test_crud_actions_require_relay_manage_scope(self) -> None:
        contributor = RelayGatewayAdminContributor()
        by_name = {action.name: action for action in contributor.get_actions()}
        for name in _ACTION_NAMES:
            assert by_name[name].permission == PERMISSION_CHANNEL_MANAGE
        assert PERMISSION_CHANNEL_MANAGE in contributor.required_permissions


class TestCreateChannel:
    async def test_create_channel_validates_required_params(self) -> None:
        store = FakeChannelStore()
        container = make_container(store)
        result = await relay_actions.create_channel(container)
        assert result["ok"] is False
        assert "name is required" in str(result["message"])
        result = await relay_actions.create_channel(container, name="  ")
        assert result["ok"] is False
        result = await relay_actions.create_channel(
            container, name="c1", upstream_base_url=""
        )
        assert result["ok"] is False

    async def test_create_channel_rejects_invalid_payload(self) -> None:
        store = FakeChannelStore()
        container = make_container(store)
        result = await relay_actions.create_channel(
            container, name="c1", upstream_base_url=BASE_URL, models=[]
        )
        assert result["ok"] is False
        result = await relay_actions.create_channel(
            container,
            name="c1",
            upstream_base_url=BASE_URL,
            models=[MODEL],
            target_format="not-a-format",
        )
        assert result["ok"] is False

    async def test_create_channel_persists_and_returns_revision(self) -> None:
        store = FakeChannelStore()
        container = make_container(store)
        result = await relay_actions.create_channel(
            container, **default_params("c1")
        )
        assert result["ok"] is True
        assert result["echo"]["name"] == "c1"
        assert result["revision"] == 1
        assert store.rows["c1"].revision == 1
        assert store.rows["c1"].channel.models == (MODEL,)

    async def test_create_channel_rejects_name_collision(self) -> None:
        store = FakeChannelStore(
            [RelayChannelSnapshot(channel=make_channel("c1"), revision=3, created_at="t", updated_at="t")]
        )
        container = make_container(store)
        result = await relay_actions.create_channel(
            container, **default_params("c1")
        )
        assert result["ok"] is False
        assert "exist" in str(result["message"])
        assert store.rows["c1"].revision == 3


class TestUpdateChannel:
    async def test_update_channel_returns_concurrency_stale_outcome(self) -> None:
        store = FakeChannelStore(
            [RelayChannelSnapshot(channel=make_channel("c1"), revision=3, created_at="t", updated_at="t")]
        )
        container = make_container(store)
        result = await relay_actions.update_channel(
            container, **default_params("c1", expected_revision=2)
        )
        assert result["ok"] is False
        assert result["code"] == "CONCURRENCY_STALE"
        assert store.rows["c1"].revision == 3

    async def test_update_channel_bumps_revision(self) -> None:
        store = FakeChannelStore(
            [RelayChannelSnapshot(channel=make_channel("c1"), revision=3, created_at="t", updated_at="t")]
        )
        container = make_container(store)
        result = await relay_actions.update_channel(
            container, **default_params("c1", expected_revision=3)
        )
        assert result["ok"] is True
        assert result["revision"] == 4
        assert store.rows["c1"].revision == 4

    async def test_update_channel_requires_revision(self) -> None:
        store = FakeChannelStore()
        container = make_container(store)
        result = await relay_actions.update_channel(
            container, **default_params("c1")
        )
        assert result["ok"] is False


class TestDeleteChannel:
    async def test_delete_channel_removes_row(self) -> None:
        store = FakeChannelStore(
            [RelayChannelSnapshot(channel=make_channel("c1"), revision=2, created_at="t", updated_at="t")]
        )
        container = make_container(store)
        result = await relay_actions.delete_channel(
            container, name="c1", expected_revision=2
        )
        assert result["ok"] is True
        assert "c1" not in store.rows

    async def test_delete_channel_stale_or_missing_is_rejected(self) -> None:
        store = FakeChannelStore(
            [RelayChannelSnapshot(channel=make_channel("c1"), revision=2, created_at="t", updated_at="t")]
        )
        container = make_container(store)
        result = await relay_actions.delete_channel(
            container, name="c1", expected_revision=1
        )
        assert result["ok"] is False
        assert result["code"] == "CONCURRENCY_STALE"
        assert "c1" in store.rows
        result = await relay_actions.delete_channel(
            container, name="ghost", expected_revision=1
        )
        assert result["ok"] is False


class TestTestChannel:
    async def test_test_channel_returns_probe_verdict(self) -> None:
        store = FakeChannelStore()
        health = make_health()
        container = make_container(store, health)
        result = await relay_actions.test_channel(
            container, name="c1"
        )
        assert result["ok"] is True
        assert result["echo"]["verdict"] == "healthy"
        assert result["echo"]["latency_ms"] == 12.0

    async def test_test_channel_unknown_name_is_rejected(self) -> None:
        store = FakeChannelStore()
        container = make_container(store, make_health())
        result = await relay_actions.test_channel(container, name="ghost")
        assert result["ok"] is False

    async def test_test_channel_requires_health_service(self) -> None:
        store = FakeChannelStore()
        container = make_container(store)
        result = await relay_actions.test_channel(container, name="c1")
        assert result["ok"] is False
        assert "health" in str(result["message"])


class TestChannelsPage:
    async def test_page_renders_stored_channels(self) -> None:
        store = FakeChannelStore(
            [
                RelayChannelSnapshot(
                    channel=make_channel("main", priority=5),
                    revision=7,
                    created_at="t",
                    updated_at="t",
                )
            ]
        )
        page = RelayGatewayChannelsPage(store=store)
        response = await page.handle(request=None)
        text = response.body.decode()
        assert "main" in text
        assert "openai_chat" in text
        assert MODEL in text
        assert "5" in text
        assert "7" in text
        assert "enabled" in text.lower()

    async def test_page_renders_empty_state(self) -> None:
        page = RelayGatewayChannelsPage(store=FakeChannelStore())
        response = await page.handle(request=None)
        assert "no channels" in response.body.decode().lower()

    async def test_page_renders_unavailable_without_store(self) -> None:
        page = RelayGatewayChannelsPage(store=None)
        response = await page.handle(request=None)
        assert "not registered" in response.body.decode().lower()


class TestContributorRegistration:
    def test_channels_page_registered(self) -> None:
        contributor = RelayGatewayAdminContributor()
        pages = {p.name: p for p in contributor.get_management_pages()}
        assert "relay_gateway_channels" in pages
        assert (
            pages["relay_gateway_channels"].handler
            == "lexigram.ai.relay.gateway.admin.pages:RelayGatewayChannelsPage"
        )