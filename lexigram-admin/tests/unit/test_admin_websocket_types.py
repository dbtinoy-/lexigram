"""Tests for admin websocket types."""

import pytest

from lexigram.admin.realtime.websocket import WSMessage, WSMessageType


class TestWSMessageType:
    """Tests for WSMessageType enum."""

    def test_client_to_server_messages(self) -> None:
        """Test client to server message types."""
        assert WSMessageType.SUBSCRIBE.value == "subscribe"
        assert WSMessageType.UNSUBSCRIBE.value == "unsubscribe"
        assert WSMessageType.ACTION.value == "action"
        assert WSMessageType.PING.value == "ping"

    def test_server_to_client_messages(self) -> None:
        """Test server to client message types."""
        assert WSMessageType.EVENT.value == "event"
        assert WSMessageType.NOTIFICATION.value == "notification"
        assert WSMessageType.ERROR.value == "error"
        assert WSMessageType.PONG.value == "pong"
        assert WSMessageType.ACK.value == "ack"

    def test_ws_message_type_members(self) -> None:
        """Test WSMessageType has expected members."""
        members = list(WSMessageType)
        assert len(members) == 9


class TestWSMessage:
    """Tests for WSMessage dataclass."""

    def test_ws_message_creation(self) -> None:
        """Test creating WSMessage."""
        msg = WSMessage(
            type=WSMessageType.EVENT,
            data={"event": "user.created"},
        )
        assert msg.type == WSMessageType.EVENT
        assert msg.data == {"event": "user.created"}
        assert msg.id is None

    def test_ws_message_with_id(self) -> None:
        """Test WSMessage with ID."""
        msg = WSMessage(
            type=WSMessageType.ACK,
            data={"status": "ok"},
            id="msg-123",
        )
        assert msg.id == "msg-123"

    def test_ws_message_to_dict(self) -> None:
        """Test WSMessage to_dict method."""
        msg = WSMessage(
            type=WSMessageType.EVENT,
            data={"event": "test"},
        )
        result = msg.to_dict()
        assert result["type"] == "event"
        assert result["data"] == {"event": "test"}
        assert "timestamp" in result

    def test_ws_message_from_dict(self) -> None:
        """Test WSMessage from_dict method."""
        data = {
            "type": "event",
            "data": {"key": "value"},
            "id": "msg-456",
        }
        msg = WSMessage.from_dict(data)
        assert msg.type == WSMessageType.EVENT
        assert msg.data == {"key": "value"}
        assert msg.id == "msg-456"

    def test_ws_message_from_dict_unknown_type(self) -> None:
        """Test WSMessage from_dict with unknown type."""
        data = {
            "type": "custom_type",
            "data": {},
        }
        msg = WSMessage.from_dict(data)
        assert msg.type == "custom_type"
