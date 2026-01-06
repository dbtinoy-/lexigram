"""Unit tests for per-subscription authorization in GraphQLWSTransport."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.graphql.subscriptions.transport import GraphQLWSTransport
from lexigram.graphql.subscriptions.transport import SubscriptionConnection


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def base_transport() -> GraphQLWSTransport:
    """Transport with connection and low-level send methods mocked.

    Provides a minimal ready-to-use transport so each test can focus on
    the authorization path without wiring up a real WebSocket or schema.
    ``_send_message`` is mocked to prevent any real WebSocket interaction;
    ``_send_error`` is mocked separately so tests can assert on it.
    """
    transport = GraphQLWSTransport()
    transport._connection = SubscriptionConnection()
    # Mock the raw send primitives so we never touch a real WebSocket
    transport._send_message = AsyncMock()  # type: ignore[method-assign]
    transport._send_error = AsyncMock()  # type: ignore[method-assign]
    # Default subscribe: returns None (non-iterator) → hits "Immediate result" branch
    # which calls _send_next/_send_complete (both routed through mocked _send_message)
    transport._subscribe = AsyncMock(return_value=None)  # type: ignore[method-assign]
    return transport


@pytest.fixture()
def transport_with_auth(base_transport: GraphQLWSTransport) -> GraphQLWSTransport:
    """Transport with a subscription auth handler wired in (default: allows all).

    Individual tests override ``authorize`` return value as needed.
    """
    auth_handler = MagicMock()
    auth_handler.authorize = AsyncMock(return_value=True)
    base_transport._subscription_auth_handler = auth_handler
    return base_transport


@pytest.fixture()
def transport_no_auth(base_transport: GraphQLWSTransport) -> GraphQLWSTransport:
    """Transport with no subscription auth handler (open access)."""
    base_transport._subscription_auth_handler = None
    return base_transport


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSubscriptionTransportAuth:
    """Verify the per-subscription authorization hook behaviour."""

    @pytest.mark.asyncio
    async def test_unauthorized_subscription_rejected(
        self,
        transport_with_auth: GraphQLWSTransport,
    ) -> None:
        """A ``False`` from the auth handler must reject the subscription.

        The transport must call ``_send_error`` and must NOT proceed to
        execute or store the subscription.
        """
        transport_with_auth._subscription_auth_handler.authorize = AsyncMock(
            return_value=False
        )

        await transport_with_auth._handle_subscribe(
            "sub-1", {"query": "subscription { onEvent }"}
        )

        transport_with_auth._send_error.assert_awaited_once()
        error_call_args = transport_with_auth._send_error.call_args
        assert error_call_args[0][0] == "sub-1"
        assert "Unauthorized" in error_call_args[0][1]
        # The subscription must not have been stored
        assert transport_with_auth._connection.get("sub-1") is None

    @pytest.mark.asyncio
    async def test_authorized_subscription_proceeds(
        self,
        transport_with_auth: GraphQLWSTransport,
    ) -> None:
        """A ``True`` from the auth handler must let the subscription continue.

        ``_send_error`` must not be called when authorization succeeds and the
        underlying subscribe callable is available.
        """
        transport_with_auth._subscription_auth_handler.authorize = AsyncMock(
            return_value=True
        )

        await transport_with_auth._handle_subscribe(
            "sub-1", {"query": "subscription { onEvent }"}
        )

        transport_with_auth._send_error.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_auth_handler_allows_all_subscriptions(
        self,
        transport_no_auth: GraphQLWSTransport,
    ) -> None:
        """When no auth handler is configured every subscription must proceed.

        This preserves backward-compatible open-access behaviour for transports
        that have not opted in to per-subscription authorization.
        """
        await transport_no_auth._handle_subscribe(
            "sub-1", {"query": "subscription { onEvent }"}
        )

        transport_no_auth._send_error.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_auth_handler_exception_rejects_subscription(
        self,
        transport_with_auth: GraphQLWSTransport,
    ) -> None:
        """An exception raised by the auth handler must reject the subscription.

        The transport must catch the error, log it, and send a generic
        ``"Authorization error"`` message without propagating the exception.
        """
        transport_with_auth._subscription_auth_handler.authorize = AsyncMock(
            side_effect=RuntimeError("backend unavailable")
        )

        await transport_with_auth._handle_subscribe(
            "sub-1", {"query": "subscription { onEvent }"}
        )

        transport_with_auth._send_error.assert_awaited_once()
        error_call_args = transport_with_auth._send_error.call_args
        assert error_call_args[0][0] == "sub-1"
        assert "Authorization error" in error_call_args[0][1]
        # Subscription must not be stored after a handler error
        assert transport_with_auth._connection.get("sub-1") is None

    @pytest.mark.asyncio
    async def test_auth_handler_receives_correct_context(
        self,
        transport_with_auth: GraphQLWSTransport,
    ) -> None:
        """The auth handler must be called with the right user, operation and query."""
        transport_with_auth._user = {"id": "u-42", "role": "admin"}
        transport_with_auth._subscription_auth_handler.authorize = AsyncMock(
            return_value=True
        )

        await transport_with_auth._handle_subscribe(
            "sub-2",
            {
                "query": "subscription OnNewPost { onNewPost { id } }",
                "operationName": "OnNewPost",
            },
        )

        transport_with_auth._subscription_auth_handler.authorize.assert_awaited_once_with(
            user={"id": "u-42", "role": "admin"},
            operation_name="OnNewPost",
            query="subscription OnNewPost { onNewPost { id } }",
        )
