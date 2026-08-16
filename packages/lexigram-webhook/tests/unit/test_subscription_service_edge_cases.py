"""Additional tests for WebhookSubscriptionService edge cases."""

from __future__ import annotations

import pytest

from lexigram.webhook.config import WebhookConfig
from lexigram.webhook.exceptions import (
    SubscriptionNotFoundError,
)
from lexigram.webhook.store.memory import InMemoryWebhookStore
from lexigram.webhook.subscription.service import WebhookSubscriptionService


@pytest.fixture
def service(store: InMemoryWebhookStore, config: WebhookConfig) -> WebhookSubscriptionService:
    return WebhookSubscriptionService(store=store, config=config)


class TestWebhookSubscriptionServiceEdgeCases:
    """Additional edge case tests for WebhookSubscriptionService."""

    @pytest.mark.asyncio
    async def test_create_with_all_parameters(
        self, service: WebhookSubscriptionService
    ) -> None:
        """create() with all optional parameters."""
        result = await service.create(
            "https://example.com/hook",
            event_types=frozenset({"user.created", "user.deleted"}),
            description="My webhook",
            tenant_id="tenant-123",
            metadata={"key": "value"},
        )
        assert result.is_ok()
        sub = result.unwrap()
        assert sub.event_types == frozenset({"user.created", "user.deleted"})
        assert sub.description == "My webhook"
        assert sub.tenant_id == "tenant-123"
        assert sub.metadata["key"] == "value"

    @pytest.mark.asyncio
    async def test_create_with_empty_string_description(
        self, service: WebhookSubscriptionService
    ) -> None:
        """create() with empty string description."""
        result = await service.create(
            "https://example.com/hook",
            description="",
        )
        assert result.is_ok()
        assert result.unwrap().description == ""

    @pytest.mark.asyncio
    async def test_create_with_null_event_types(
        self, service: WebhookSubscriptionService
    ) -> None:
        """create() with event_types=None means all events."""
        result = await service.create(
            "https://example.com/hook",
            event_types=None,
        )
        assert result.is_ok()
        assert result.unwrap().event_types is None

    @pytest.mark.asyncio
    async def test_get_returns_ok_for_existing(
        self, service: WebhookSubscriptionService
    ) -> None:
        """get() returns Ok for existing subscription."""
        create_result = await service.create("https://example.com/hook")
        sub_id = create_result.unwrap().subscription_id

        get_result = await service.get(sub_id)
        assert get_result.is_ok()

    @pytest.mark.asyncio
    async def test_list_with_no_filters(
        self, service: WebhookSubscriptionService
    ) -> None:
        """list() with no filters returns all active."""
        await service.create("https://a.example.com/hook")
        await service.create("https://b.example.com/hook")

        subs = await service.list(active_only=True)
        assert len(subs) == 2

    @pytest.mark.asyncio
    async def test_list_inactive_only(
        self, service: WebhookSubscriptionService
    ) -> None:
        """list() with active_only=False includes inactive."""
        result = await service.create("https://example.com/hook")
        sub_id = result.unwrap().subscription_id
        await service.deactivate(sub_id)

        subs = await service.list(active_only=False)
        assert len(subs) == 1

    @pytest.mark.asyncio
    async def test_list_filters_by_event_type(
        self, service: WebhookSubscriptionService
    ) -> None:
        """list() filters by event_type."""
        await service.create(
            "https://a.example.com/hook",
            event_types=frozenset({"user.created"}),
        )
        await service.create(
            "https://b.example.com/hook",
            event_types=frozenset({"order.placed"}),
        )

        subs = await service.list(event_type="user.created")
        assert len(subs) == 1

    @pytest.mark.asyncio
    async def test_list_pagination(
        self, service: WebhookSubscriptionService
    ) -> None:
        """list() respects limit and offset."""
        for i in range(5):
            await service.create(f"https://{i}.example.com/hook")

        subs = await service.list(limit=2, offset=2)
        assert len(subs) == 2

    @pytest.mark.asyncio
    async def test_list_filters_by_tenant(
        self, service: WebhookSubscriptionService
    ) -> None:
        """list() filters by tenant_id."""
        await service.create(
            "https://a.example.com/hook",
            tenant_id="tenant-a",
        )
        await service.create(
            "https://b.example.com/hook",
            tenant_id="tenant-b",
        )

        subs = await service.list(tenant_id="tenant-a")
        assert len(subs) == 1

    @pytest.mark.asyncio
    async def test_update_event_types_to_none(
        self, service: WebhookSubscriptionService
    ) -> None:
        """update_event_types() can set to None (all events)."""
        result = await service.create(
            "https://example.com/hook",
            event_types=frozenset({"user.created"}),
        )
        sub_id = result.unwrap().subscription_id

        update_result = await service.update_event_types(sub_id, None)
        assert update_result.is_ok()
        assert update_result.unwrap().event_types is None

    @pytest.mark.asyncio
    async def test_activate_deactivated_subscription(
        self, service: WebhookSubscriptionService
    ) -> None:
        """activate() reactivates a deactivated subscription."""
        result = await service.create("https://example.com/hook")
        sub_id = result.unwrap().subscription_id

        await service.deactivate(sub_id)
        activate_result = await service.activate(sub_id)

        assert activate_result.is_ok()
        get_result = await service.get(sub_id)
        assert get_result.unwrap().active is True

    @pytest.mark.asyncio
    async def test_activate_already_active_returns_ok(
        self, service: WebhookSubscriptionService
    ) -> None:
        """activate() returns Ok for already active subscription."""
        result = await service.create("https://example.com/hook")
        sub_id = result.unwrap().subscription_id

        activate_result = await service.activate(sub_id)
        assert activate_result.is_ok()

    @pytest.mark.asyncio
    async def test_activate_missing_returns_err(
        self, service: WebhookSubscriptionService
    ) -> None:
        """activate() returns Err for missing subscription."""
        result = await service.activate("missing-id")
        assert result.is_err()


class TestWebhookSubscriptionServiceErrorHandling:
    """Error handling tests for WebhookSubscriptionService."""

    @pytest.mark.asyncio
    async def test_create_empty_url_returns_err(
        self, service: WebhookSubscriptionService
    ) -> None:
        """create() with empty URL returns Err."""
        result = await service.create("")
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_create_malformed_url_returns_err(
        self, service: WebhookSubscriptionService
    ) -> None:
        """create() with malformed URL returns Err."""
        result = await service.create("not-a-url")
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_update_event_types_missing_returns_err(
        self, service: WebhookSubscriptionService
    ) -> None:
        """update_event_types() returns Err for missing subscription."""
        result = await service.update_event_types("missing-id", frozenset({"test"}))
        assert result.is_err()
        assert isinstance(result.unwrap_err(), SubscriptionNotFoundError)

    @pytest.mark.asyncio
    async def test_rotate_secret_missing_returns_err(
        self, service: WebhookSubscriptionService
    ) -> None:
        """rotate_secret() returns Err for missing subscription."""
        result = await service.rotate_secret("missing-id")
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_deactivate_already_inactive_still_returns_ok(
        self, service: WebhookSubscriptionService
    ) -> None:
        """deactivate() returns Ok even for already inactive subscription (idempotent)."""
        result = await service.create("https://example.com/hook")
        sub_id = result.unwrap().subscription_id

        await service.deactivate(sub_id)
        deactivate_result = await service.deactivate(sub_id)
        # deactivate is idempotent - still returns Ok
        assert deactivate_result.is_ok()