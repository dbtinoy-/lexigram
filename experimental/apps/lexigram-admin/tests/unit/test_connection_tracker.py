"""Tests for ConnectionTracker — extracted collaborator from AdminWebSocketManager."""

from __future__ import annotations

import pytest

from lexigram.admin.realtime.connection_tracker import ConnectionTracker


@pytest.fixture
def tracker() -> ConnectionTracker:
    return ConnectionTracker()


class TestConnect:
    @pytest.mark.asyncio
    async def test_connect_returns_connection_id(
        self, tracker: ConnectionTracker
    ) -> None:
        conn_id = await tracker.connect("ws1")
        assert isinstance(conn_id, str)
        assert len(conn_id) > 0

    @pytest.mark.asyncio
    async def test_connect_stores_connection(self, tracker: ConnectionTracker) -> None:
        conn_id = await tracker.connect("ws1")
        assert tracker.get_connection(conn_id) == "ws1"

    @pytest.mark.asyncio
    async def test_connect_with_user(self, tracker: ConnectionTracker) -> None:
        conn_id = await tracker.connect("ws1", user_id="user-1")
        assert tracker.get_user_connection_count("user-1") == 1


class TestDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(
        self, tracker: ConnectionTracker
    ) -> None:
        conn_id = await tracker.connect("ws1")
        await tracker.disconnect(conn_id)
        assert tracker.get_connection(conn_id) is None

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up_subscriptions(
        self, tracker: ConnectionTracker
    ) -> None:
        conn_id = await tracker.connect("ws1")
        await tracker.subscribe(conn_id, ["users"])
        await tracker.disconnect(conn_id)
        assert conn_id not in tracker.get_resource_subscribers("users")

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up_user_mapping(
        self, tracker: ConnectionTracker
    ) -> None:
        conn_id = await tracker.connect("ws1", user_id="user-1")
        await tracker.disconnect(conn_id)
        assert tracker.get_user_connection_count("user-1") == 0


class TestSubscribeUnsubscribe:
    @pytest.mark.asyncio
    async def test_subscribe_adds_to_resource(self, tracker: ConnectionTracker) -> None:
        conn_id = await tracker.connect("ws1")
        await tracker.subscribe(conn_id, ["users", "orders"])
        assert conn_id in tracker.get_resource_subscribers("users")
        assert conn_id in tracker.get_resource_subscribers("orders")

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_from_resource(
        self, tracker: ConnectionTracker
    ) -> None:
        conn_id = await tracker.connect("ws1")
        await tracker.subscribe(conn_id, ["users"])
        await tracker.unsubscribe(conn_id, ["users"])
        assert conn_id not in tracker.get_resource_subscribers("users")

    @pytest.mark.asyncio
    async def test_get_connection_resources(self, tracker: ConnectionTracker) -> None:
        conn_id = await tracker.connect("ws1")
        await tracker.subscribe(conn_id, ["users", "orders"])
        resources = tracker.get_connection_resources(conn_id)
        assert "users" in resources
        assert "orders" in resources


class TestConnectionCount:
    @pytest.mark.asyncio
    async def test_connection_count(self, tracker: ConnectionTracker) -> None:
        assert tracker.connection_count == 0
        await tracker.connect("ws1")
        assert tracker.connection_count == 1
        await tracker.connect("ws2")
        assert tracker.connection_count == 2
        conn_id = await tracker.connect("ws3")
        await tracker.disconnect(conn_id)
        assert tracker.connection_count == 2


class TestTargetResolution:
    @pytest.mark.asyncio
    async def test_resolve_targets_by_resource(
        self, tracker: ConnectionTracker
    ) -> None:
        c1 = await tracker.connect("ws1")
        c2 = await tracker.connect("ws2")
        await tracker.subscribe(c1, ["users"])
        await tracker.subscribe(c2, ["users"])
        targets = tracker.resolve_targets(resource="users")
        assert c1 in targets
        assert c2 in targets

    @pytest.mark.asyncio
    async def test_resolve_targets_by_user(self, tracker: ConnectionTracker) -> None:
        c1 = await tracker.connect("ws1", user_id="user-1")
        c2 = await tracker.connect("ws2", user_id="user-2")
        await tracker.subscribe(c1, ["users"])
        await tracker.subscribe(c2, ["users"])
        targets = tracker.resolve_targets(user_ids=["user-1"])
        assert c1 in targets
        assert c2 not in targets

    @pytest.mark.asyncio
    async def test_resolve_targets_exclude(self, tracker: ConnectionTracker) -> None:
        c1 = await tracker.connect("ws1")
        c2 = await tracker.connect("ws2")
        await tracker.subscribe(c1, ["users"])
        await tracker.subscribe(c2, ["users"])
        targets = tracker.resolve_targets(resource="users", exclude_connections=[c1])
        assert c1 not in targets
        assert c2 in targets

    @pytest.mark.asyncio
    async def test_resolve_targets_all_when_no_filter(
        self, tracker: ConnectionTracker
    ) -> None:
        c1 = await tracker.connect("ws1")
        c2 = await tracker.connect("ws2")
        targets = tracker.resolve_targets()
        assert c1 in targets
        assert c2 in targets
