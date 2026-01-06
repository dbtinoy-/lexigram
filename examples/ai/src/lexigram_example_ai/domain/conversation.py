"""Conversation domain model.

A :class:`Conversation` tracks the full message history for a single chat
session.  :class:`Message` is an immutable value object representing one
turn.  When a conversation is created a :class:`ConversationStarted` domain
event is emitted so downstream listeners can react without polling.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from lexigram.contracts.domain.events import DomainEvent


class MessageRole(StrEnum):
    """Role of a participant in a conversation turn.

    Attributes:
        SYSTEM: Instructions injected before the conversation.
        USER: Human participant turn.
        ASSISTANT: AI model turn.
    """

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class Message:
    """Immutable value object representing a single conversation turn.

    Attributes:
        role: Who sent this message.
        content: Text content of the message.
        created_at: UTC timestamp when the message was added.
        metadata: Optional provider-specific or application metadata.
    """

    role: MessageRole
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConversationStarted(DomainEvent):
    """Emitted when a new conversation session is created.

    Attributes:
        session_id: Unique identifier of the new conversation.
        title: Human-readable title for the session.
    """

    session_id: str = ""
    title: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialise the event to a plain dictionary.

        Returns:
            Dictionary representation including base event fields.
        """
        return {
            **super().to_dict(),
            "session_id": self.session_id,
            "title": self.title,
        }


@dataclass
class Conversation:
    """Entity representing an ongoing multi-turn chat session.

    A conversation accumulates :class:`Message` value objects and emits
    :class:`ConversationStarted` on construction.  Token budgeting and
    history truncation are delegated to the pipeline layer so the domain
    model stays free of infrastructure concerns.

    Attributes:
        id: Unique conversation identifier (UUID4).
        session_id: External session identifier (e.g. from a web client).
        title: Human-readable title for the conversation.
        messages: Ordered list of messages in this conversation.
        created_at: UTC timestamp of conversation creation.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    messages: list[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    _domain_events: list[DomainEvent] = field(
        default_factory=list, repr=False, compare=False
    )

    @classmethod
    def start(
        cls,
        *,
        session_id: str | None = None,
        title: str = "",
    ) -> Conversation:
        """Factory method — create a new conversation and emit the started event.

        Args:
            session_id: External session identifier.  A UUID is generated when
                ``None`` is supplied.
            title: Optional human-readable label.

        Returns:
            A freshly initialised :class:`Conversation` with one pending event.
        """
        sid = session_id or str(uuid.uuid4())
        conversation = cls(session_id=sid, title=title)
        conversation._domain_events.append(
            ConversationStarted(session_id=sid, title=title)
        )
        return conversation

    def add_message(self, *, role: MessageRole, content: str) -> Message:
        """Append a new message to the conversation history.

        Args:
            role: The role of the participant sending this message.
            content: Text content of the message.

        Returns:
            The newly created :class:`Message` value object.
        """
        message = Message(role=role, content=content)
        self.messages.append(message)
        return message

    def pop_events(self) -> list[DomainEvent]:
        """Drain and return pending domain events.

        Returns:
            All domain events accumulated since the last call to this method.
        """
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    @property
    def message_count(self) -> int:
        """Total number of messages in this conversation."""
        return len(self.messages)

    @property
    def last_message(self) -> Message | None:
        """The most recent message, or ``None`` if the conversation is empty."""
        return self.messages[-1] if self.messages else None


__all__ = [
    "Conversation",
    "ConversationStarted",
    "Message",
    "MessageRole",
]
