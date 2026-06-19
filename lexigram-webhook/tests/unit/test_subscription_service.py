"""Tests for WebhookSubscriptionService."""

from __future__ import annotations
from enum import Enum

import pytest

from lexigram.webhook.config import WebhookConfig
from lexigram.webhook.exceptions import (
    InvalidWebhookURLError,
    SubscriptionNotFoundError,
)
from lexigram.webhook.store.memory import InMemoryWebhookStore
from lexigram.webhook.subscription.service import WebhookSubscriptionService


@pytest.fixture
def service(store: InMemoryWebhookStore, config: WebhookConfig) -> WebhookSubscriptionService:
    """WebhookSubscriptionService wired with in-memory store."""
    return WebhookSubscriptionService(store=store, config=config)


class TestWebhookSubscriptionService:
    """Tests for WebhookSubscriptionService."""

    @pytest.mark.asyncio
    async def test_create_valid_url(
        self, service: WebhookSubscriptionService
    ) -> None:
        """create() with valid URL returns Ok(subscription)."""
        result = await service.create("https://example.com/hook")
        assert result.is_ok()
        sub = result.unwrap()
        assert sub.url == "https://example.com/hook"
        assert sub.subscription_id
        assert sub.secret
        assert sub.active is True

    @pytest.mark.asyncio
    async def test_create_http_url_allowed_when_opt_in(
        self, store: InMemoryWebhookStore
    ) -> None:
        """create() allows loopback http:// only when allow_private_urls=True."""
        service = WebhookSubscriptionService(
            store=store,
            config=WebhookConfig(allow_private_urls=True),
        )
        result = await service.create("http://localhost:8080/hook")
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_create_blocks_loopback_by_default(
        self, service: WebhookSubscriptionService
    ) -> None:
        """create() rejects loopback URLs by default (fail-closed)."""
        result = await service.create("http://127.0.0.1:8080/hook")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), InvalidWebhookURLError)

    @pytest.mark.asyncio
    async def test_create_blocks_private_ip_by_default(
        self, service: WebhookSubscriptionService
    ) -> None:
        """create() rejects RFC1918 URLs by default."""
        result = await service.create("http://192.168.1.10/hook")
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_create_allows_public_hostname(
        self, service: WebhookSubscriptionService
    ) -> None:
        """create() allows public hostnames (resolved via fake DNS)."""
        result = await service.create("https://example.com/hook")
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_create_invalid_url_returns_err(
        self, service: WebhookSubscriptionService
    ) -> None:
        """create() with invalid URL returns Err(InvalidWebhookURLError)."""
        result = await service.create("ftp://bad-url")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), InvalidWebhookURLError)

    @pytest.mark.asyncio
    async def test_get_existing(
        self, service: WebhookSubscriptionService
    ) -> None:
        """get() returns Ok(subscription) for existing subscription."""
        create_result = await service.create("https://example.com/hook")
        sub_id = create_result.unwrap().subscription_id

        get_result = await service.get(sub_id)
        assert get_result.is_ok()
        assert get_result.unwrap().subscription_id == sub_id

    @pytest.mark.asyncio
    async def test_get_missing_returns_err(
        self, service: WebhookSubscriptionService
    ) -> None:
        """get() returns Err(SubscriptionNotFoundError) for missing ID."""
        result = await service.get("nonexistent-id")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), SubscriptionNotFoundError)

    @pytest.mark.asyncio
    async def test_rotate_secret_preserves_old_in_metadata(
        self, service: WebhookSubscriptionService
    ) -> None:
        """rotate_secret() stores old secret in metadata and generates new one."""
        create_result = await service.create("https://example.com/hook")
        sub = create_result.unwrap()
        old_secret = sub.secret

        rotate_result = await service.rotate_secret(sub.subscription_id)
        assert rotate_result.is_ok()
        updated = rotate_result.unwrap()

        assert updated.secret != old_secret
        assert updated.metadata.get("previous_secret") == old_secret
        assert "previous_secret_expires" in updated.metadata

    @pytest.mark.asyncio
    async def test_deactivate(
        self, service: WebhookSubscriptionService
    ) -> None:
        """deactivate() sets active=False."""
        create_result = await service.create("https://example.com/hook")
        sub_id = create_result.unwrap().subscription_id

        result = await service.deactivate(sub_id)
        assert result.is_ok()

        get_result = await service.get(sub_id)
        assert get_result.unwrap().active is False

    @pytest.mark.asyncio
    async def test_activate(
        self, service: WebhookSubscriptionService
    ) -> None:
        """activate() sets active=True after deactivation."""
        create_result = await service.create("https://example.com/hook")
        sub_id = create_result.unwrap().subscription_id

        await service.deactivate(sub_id)
        result = await service.activate(sub_id)
        assert result.is_ok()

        get_result = await service.get(sub_id)
        assert get_result.unwrap().active is True

    @pytest.mark.asyncio
    async def test_deactivate_missing_returns_err(
        self, service: WebhookSubscriptionService
    ) -> None:
        """deactivate() on unknown ID returns Err."""
        result = await service.deactivate("nonexistent")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), SubscriptionNotFoundError)

    @pytest.mark.asyncio
    async def test_update_event_types(
        self, service: WebhookSubscriptionService
    ) -> None:
        """update_event_types() persists new filter."""
        create_result = await service.create("https://example.com/hook")
        sub_id = create_result.unwrap().subscription_id

        result = await service.update_event_types(
            sub_id, frozenset({"user.created", "user.deleted"})
        )
        assert result.is_ok()
        updated = result.unwrap()
        assert updated.event_types == frozenset({"user.created", "user.deleted"})

    @pytest.mark.asyncio
    async def test_list_returns_subscriptions(
        self, service: WebhookSubscriptionService
    ) -> None:
        """list() returns all active subscriptions."""
        await service.create("https://a.example.com/hook")
        await service.create("https://b.example.com/hook")
        subs = await service.list()
        assert len(subs) == 2

    @pytest.mark.asyncio
    async def test_create_with_event_types(
        self, service: WebhookSubscriptionService
    ) -> None:
        """create() stores event_types correctly."""
        result = await service.create(
            "https://example.com/hook",
            event_types=frozenset({"order.placed"}),
        )
        assert result.is_ok()
        sub = result.unwrap()
        assert sub.event_types == frozenset({"order.placed"})
