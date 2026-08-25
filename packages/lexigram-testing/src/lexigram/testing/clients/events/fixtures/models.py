"""Shared minimal domain model classes for the events testing fixtures.

These sample events, commands, queries, and aggregates mirror the
``lexigram-events`` domain primitives and fall back to inert stand-ins when
the events extension is not installed.
"""

from __future__ import annotations

# mypy: disable-error-code = annotation-unchecked
from typing import Any
from uuid import UUID

try:
    from lexigram.events import AggregateRoot, Command, Event, Query
except (
    ImportError,
    ModuleNotFoundError,
):  # pragma: no cover - defensive fallback for import-time issues

    class Event:  # type: ignore[no-redef]
        pass

    class Command:  # type: ignore[no-redef]
        pass

    class Query:  # type: ignore[no-redef]
        pass

    class AggregateRoot:  # type: ignore[no-redef]
        pass


class UserCreatedEvent(Event):
    aggregate_id: UUID
    user_id: UUID
    name: str
    email: str


class UserUpdatedEvent(Event):
    aggregate_id: UUID
    user_id: UUID
    name: str | None = None
    email: str | None = None


class OrderCreatedEvent(Event):
    aggregate_id: UUID
    order_id: UUID
    user_id: UUID
    amount: float


class UserRegisteredIntegrationEvent(Event):
    aggregate_id: UUID
    user_id: UUID
    email: str
    source: str = "web"


class OrderShippedIntegrationEvent(Event):
    aggregate_id: UUID
    order_id: UUID
    tracking_number: str
    carrier: str


class CreateUserCommand(Command):
    name: str
    email: str


class UpdateUserCommand(Command):
    user_id: UUID
    name: str | None = None
    email: str | None = None


class DeleteUserCommand(Command):
    user_id: UUID


class CreateOrderCommand(Command):
    user_id: UUID
    amount: float
    items: list[dict[str, Any]]


class GetUserQuery(Query):
    user_id: UUID


class ListUsersQuery(Query):
    limit: int = 10
    offset: int = 0
    name_filter: str | None = None


class GetOrderQuery(Query):
    order_id: UUID


class ListOrdersQuery(Query):
    user_id: UUID | None = None
    status: str | None = None
    limit: int = 10


class UserAggregate(AggregateRoot):
    name: str
    email: str
    is_active: bool = True

    def update_name(self, new_name: str) -> Any:
        self.name = new_name
        self.updated_at = getattr(self, "updated_at", None)


class OrderAggregate(AggregateRoot):
    user_id: UUID
    amount: float
    status: str = "pending"

    def complete(self) -> Any:
        if self.status != "pending":
            raise ValueError("Can only complete pending orders")
        self.status = "completed"


class TestEvent(Event):
    aggregate_id: UUID
    index: int
    data: str


class TestCommand(Command):
    index: int
    data: str
