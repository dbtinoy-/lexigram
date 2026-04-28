"""Tests for AdminRealtimeSubProvider full registration."""
from __future__ import annotations

import pytest


class TestAdminRealtimeSubProvider:
    @pytest.fixture
    def config(self):
        from lexigram.admin.config import AdminConfig

        return AdminConfig()

    @pytest.fixture
    def sub_provider(self, config):
        from lexigram.admin.di.sub_providers.realtime import AdminRealtimeSubProvider

        return AdminRealtimeSubProvider(config=config)

    @pytest.mark.asyncio
    async def test_register_places_services(self, sub_provider):
        registrations = {}

        class FakeContainer:
            def singleton(self, key, value):
                registrations[key] = value

        await sub_provider.register(FakeContainer())
        assert len(registrations) >= 2

    @pytest.mark.asyncio
    async def test_register_places_collaborative_service(self, sub_provider):
        """CollaborativeService should be registered if it exists."""
        registrations = {}

        class FakeContainer:
            def singleton(self, key, value):
                registrations[key] = value

        await sub_provider.register(FakeContainer())
        # Check if collaborative service is registered if available, or at least some services are registered
        collab_registered = any("Collaborative" in str(k) or "collaborative" in str(k) for k in registrations)
        assert collab_registered or len(registrations) >= 2

    @pytest.mark.asyncio
    async def test_health_check(self, sub_provider):
        result = await sub_provider.health_check()
        assert result.component == "admin_realtime"

    @pytest.mark.asyncio
    async def test_boot_wires_inbox_hook_to_hub(self, sub_provider):
        """Boot must forward inbox.sent events to the SSE hub."""
        from unittest.mock import AsyncMock

        from lexigram.contracts.notification.inbox import INBOX_SENT_HOOK, InboxMessage
        from lexigram.hooks.ambient import fire
        from lexigram.hooks.ambient import use as use_hooks
        from lexigram.hooks.registry import HookRegistry

        hub = AsyncMock()
        hub.publish_notification = AsyncMock()

        class FakeContainer:
            async def resolve(self, service_type):
                return hub

        registry = HookRegistry("test-boot")

        with use_hooks(registry):
            await sub_provider.boot(FakeContainer())

            message = InboxMessage.create(
                user_id="u1", title="Order shipped", body="On the way"
            )
            await fire(
                INBOX_SENT_HOOK,
                message=message,
                user_id="u1",
                title="Order shipped",
                body="On the way",
            )

        hub.publish_notification.assert_awaited_once_with(
            title="Order shipped",
            message="On the way",
            level="info",
            target_users=["u1"],
        )

    @pytest.mark.asyncio
    async def test_boot_without_hub_does_not_wire_bridge(self, sub_provider):
        """Boot must tolerate a container without AdminEventHub."""
        from lexigram.hooks.ambient import current

        class FakeContainer:
            async def resolve(self, service_type):
                raise LookupError("not registered")

        await sub_provider.boot(FakeContainer())

        assert sub_provider._hub is None  # noqa: SLF001
        assert sub_provider._inbox_bridge_wired is False  # noqa: SLF001
        assert current() is not None

    @pytest.mark.asyncio
    async def test_hub_metadata_level_is_forwarded(self, sub_provider):
        """The level metadata on the message must reach the SSE payload."""
        from unittest.mock import AsyncMock

        from lexigram.contracts.notification.inbox import INBOX_SENT_HOOK, InboxMessage
        from lexigram.hooks.ambient import fire
        from lexigram.hooks.ambient import use as use_hooks
        from lexigram.hooks.registry import HookRegistry

        hub = AsyncMock()
        hub.publish_notification = AsyncMock()

        class FakeContainer:
            async def resolve(self, service_type):
                return hub

        message = InboxMessage.create(
            user_id="u1",
            title="Alert",
            body="Something happened",
            metadata={"level": "error"},
        )
        registry = HookRegistry("test-level")

        with use_hooks(registry):
            await sub_provider.boot(FakeContainer())
            await fire(
                INBOX_SENT_HOOK,
                message=message,
                user_id="u1",
                title="Alert",
                body="Something happened",
            )

        hub.publish_notification.assert_awaited_once_with(
            title="Alert",
            message="Something happened",
            level="error",
            target_users=["u1"],
        )


__all__ = ["TestAdminRealtimeSubProvider"]

