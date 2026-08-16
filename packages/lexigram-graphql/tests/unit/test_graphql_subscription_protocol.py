"""Tests for GraphQL subscription protocol types."""

import pytest

from lexigram.graphql.subscriptions.protocol import (
    DEFAULT_CONNECTION_TIMEOUT,
    DEFAULT_KEEPALIVE_INTERVAL,
    ERROR_CODE_AUTH_INVALID,
    ERROR_CODE_AUTH_NOT_SUPPORTED,
    ERROR_CODE_BAD_REQUEST,
    ERROR_CODE_INTERNAL,
    ERROR_CODE_OPERATION_RESULT,
    GQLWSMessageType,
    PROTOCOL_NAME_LEGACY,
    PROTOCOL_NAME_TRANSPORT_WS,
)


class TestGQLWSMessageType:
    """Tests for GQLWSMessageType enum."""

    def test_connection_messages(self) -> None:
        """Test connection message types."""
        assert GQLWSMessageType.CONNECTION_INIT.value == "connection_init"
        assert GQLWSMessageType.CONNECTION_ACK.value == "connection_ack"
        assert GQLWSMessageType.CONNECTION_ERROR.value == "connection_error"
        assert GQLWSMessageType.CONNECTION_KEEP_ALIVE.value == "ka"

    def test_subscription_messages(self) -> None:
        """Test subscription message types."""
        assert GQLWSMessageType.SUBSCRIBE.value == "subscribe"
        assert GQLWSMessageType.NEXT.value == "next"
        assert GQLWSMessageType.ERROR.value == "error"
        assert GQLWSMessageType.COMPLETE.value == "complete"

    def test_ping_pong_messages(self) -> None:
        """Test ping/pong message types."""
        assert GQLWSMessageType.PING.value == "ping"
        assert GQLWSMessageType.PONG.value == "pong"

    def test_all_members(self) -> None:
        """Test all members are present."""
        members = list(GQLWSMessageType)
        assert len(members) == 10

    def test_from_string(self) -> None:
        """Test creating from string."""
        assert GQLWSMessageType("connection_init") == GQLWSMessageType.CONNECTION_INIT
        assert GQLWSMessageType("next") == GQLWSMessageType.NEXT


class TestProtocolConstants:
    """Tests for protocol constants."""

    def test_protocol_names(self) -> None:
        """Test protocol names."""
        assert PROTOCOL_NAME_LEGACY == "graphql-ws"
        assert PROTOCOL_NAME_TRANSPORT_WS == "graphql-transport-ws"

    def test_default_timeouts(self) -> None:
        """Test default timeout values."""
        assert DEFAULT_KEEPALIVE_INTERVAL == 30.0
        assert DEFAULT_CONNECTION_TIMEOUT == 10.0

    def test_error_codes(self) -> None:
        """Test error codes."""
        assert ERROR_CODE_INTERNAL == "INTERNAL_ERROR"
        assert ERROR_CODE_AUTH_NOT_SUPPORTED == "AUTH_NOT_SUPPORTED"
        assert ERROR_CODE_AUTH_INVALID == "AUTH_INVALID"
        assert ERROR_CODE_BAD_REQUEST == "BAD_REQUEST"
        assert ERROR_CODE_OPERATION_RESULT == "OPERATION_RESULT_ERROR"
